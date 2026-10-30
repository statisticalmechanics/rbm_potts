#!/usr/bin/env python
# # Learning 2d $q$-state Potts Model with Cartegorical RBM
# Kai Zhang, The Univeristy of Texas at Tyler, 2026

import os
from os import path
import sys
import matplotlib.pyplot as plt
import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F

from torchvision import datasets, transforms
from torch.utils.data import DataLoader, Dataset, random_split

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class OneHotTransform:
    def __init__(self, q):
        self.q = q

    def __call__(self, x):
        # x is a 1D tensor of integers: shape (L*L,)
        # Output will be (L*L, q) or with transpose (q, L*L)
        return torch.nn.functional.one_hot(x.long(), num_classes=self.q).float()  #.transpose(0, 1)

class PottsDataset(Dataset):
    def __init__(self, npy_path='./', q=4, transform=None):
        self.data = np.load(npy_path)  # numpy array (n_samples, L*L)
        self.data = torch.from_numpy(self.data).long()  # convert to tensor (int64)

        filename = os.path.basename(npy_path)
        T = float(filename.split("T")[1].split(".npy")[0])
        self.T_label = torch.tensor(T).float()  # regression label

        Tc = 1.0 / np.log(1.0 + np.sqrt(q))
        self.phase_label = torch.tensor(0 if T < Tc else 1).long()  # Phase classification label

        self.q = q
        self.transform = transform

    def __len__(self):
        return self.data.shape[0]

    def __getitem__(self, idx):
        x = self.data[idx]  # shape (L*L,)
        if self.transform:
            x = self.transform(x)
        return x, self.T_label  #, self.phase_label

class RBM_multinomial(nn.Module):
    """
    RBM with categorical visible and binary hidden units
    parameters: W
    visible units v are represented by one-hot vectors
    learning with Markov Chain Monte Carlo methods
    CD-k or PCD-k 
    update parameters for one batch
    calculate data visible energy and model visible energy
    difference between data and model visible energies
    one-step reconstruction cross-entropy
    """
    def __init__(self, n_class, n_visible, n_hidden, mf=False):
        super(RBM_multinomial, self).__init__()
        self.n_visible = n_visible  # nv
        self.n_hidden = n_hidden  # nh
        self.n_class = n_class # C

        # Model parameters
        self.W = nn.Parameter(torch.randn(n_hidden, n_visible*n_class) * 0.01)  # (nh, nv*C)
        self.v_bias = nn.Parameter(torch.zeros(n_visible*n_class))  # (nv*C, )
        self.h_bias = nn.Parameter(torch.zeros(n_hidden))  # (nh, )

        # Initialize persistent chain
        self.persistent_v = None
        self.mean_field = mf

    def xi(self, v):
        """
        v^T W^T + c
        input_shape: [batch_size, nv*C]
        output shape: [batch_size, nh]
        """
        return F.linear(v, self.W, self.h_bias)

    def omega(self, h):
        """
        h^TW + b
        input_shape: [batch_size, nh]
        output shape: [batch_size, nv*C]
        """
        return F.linear(h, self.W.t(), self.v_bias)

    def bernoulli_sampling(self, p):
        """Sampling from a Bernoulli distribution with prob p."""
        return torch.bernoulli(p)

    def v_to_h(self, v):
        """
        Compute p(h|v) = sigmoid(Wv + c)
        and sample v -> h
        input_shape: [batch_size, nv*C]
        output shape: [batch_size, nh]
        """
        p_h = torch.sigmoid(self.xi(v))
        return self.bernoulli_sampling(p_h)

    def h_to_v(self, h):
        """
        logits = h^TW + b # [batch_size, nv*C]
        probability p(v|h) = softmax(logits) -> # [batch_size*nv, C]
        multinomial distribution
        input_shape: [batch_size, nh]
        output shape: [batch_size, nv*C]
        """
        logits = self.omega(h)  # [batch_size, nv*C]
        # logits = logits.view(-1, self.n_visible, self.n_class)  # [batch_size, nv, C]
        logits = logits.view(-1, self.n_class)  # [batch_size*nv, C]
        p_v = F.softmax(logits, dim=-1)  # [batch_size*nv, C]
        # p_v_flat = p_v.view(-1, self.n_class)  # [batch_size*nv, C]
        samples = torch.multinomial(p_v, num_samples=1) # categorical {0,...,C-1}, [batch_size*nv, 1]
        v_sample = F.one_hot(samples.squeeze(1), num_classes=self.n_class)  # [batch_size*nv, C]
        v_sample = v_sample.view(-1, self.n_visible * self.n_class).float()  # [batch_size, nv*C]
        # p_v = p_v.view(-1, self.n_visible * self.n_class) # [batch_size, nv*C]
        return v_sample

    # def h_to_v_binary(self, h):
        # if self.mean_field == False: # binary v=0,1
        #    return self.bernoulli_sampling(p_v)
        # else:  # mean-field 0<v<1      
        #    return p_v

    def langevin_update(self, v, epsilon=0.1):
        """
        One Langevin step: v(t+1) = v(t) - epsilon^2/2 * dE/dv + epsilon*noise
        """
        v = v.view(-1, self.n_visible*self.n_class)  # [batch_size, nv]

        # if to use auto_diff
        # v = v.detach().clone().requires_grad_(True)
        # E = self.visible_energy(v).sum()
        # grad_v = torch.autograd.grad(E, v)[0] # dE/dv

        # if to calculate gradient dE/dv manually
        grad_v = -self.v_bias.t() - torch.sigmoid(self.xi(v)) @ self.W  # [batch_size, nv]

        # Gaussian noise
        noise = torch.randn_like(v)  # [batch_size, nv]

        # Langevin update
        v_new = v - (epsilon**2/2.) * grad_v + epsilon * noise

        # absorbing (0,1)
        return v_new.clamp(0,1)  #torch.sigmoid(v_new).detach()

    def forward(self, v, mc='gibbs', k=1, epsilon=0.1):
        """
        Performs k-step Gibbs sampling v->h->v' or
        k-step Langevin dynamics sampling v->v'
        """
        v = v.view(-1, self.n_visible*self.n_class)  # [batch_size, nv]

        if mc == 'gibbs':
            with torch.no_grad():  # Gibbs does not need to do auto_diff
                for _ in range(k):
                    h = self.v_to_h(v)
                    v = self.h_to_v(h)

        elif mc == 'langevin':  # Langevin MUST keep autograd to use it
            for _ in range(k):
                v = self.langevin_update(v, epsilon)
            # v = self.bernoulli_sampling(v.detach())

        return v  #.detach()   

    def visible_energy(self, v):
        """Compute the visible energy E(v)."""
        vbias_term = v.mv(self.v_bias)  # b^T v: [batch_size, nv*C] x [nv*C, 1] = [batch_size, 1]
        wxv_c = self.xi(v)  # Wv + c: [batch_size, nh]
        hidden_term = torch.sum(F.softplus(wxv_c), dim=1)  # [batch_size, 1]
        return -vbias_term - hidden_term

    def contrastive_divergence(self, v0, pcd=False, mc='gibbs', k=1, epsilon=0.1, lr=0.001):
        """
        Perform gradient descent for one batch
        with k-step Contrastive Divergence 
        """
        v_batch = v0.view(-1, self.n_visible*self.n_class)  # [batch_size, nv*C] 
        p_h_batch = torch.sigmoid(self.xi(v_batch))  # [batch_size, nh]

        # Initialize persistent chain the first time
        if self.persistent_v is None:
            self.persistent_v = v_batch.detach().clone()

        # data term
        self.W.grad = -torch.matmul(p_h_batch.t(), v_batch)/v_batch.size(0)  # [nh, nv]
        self.h_bias.grad = -torch.mean(p_h_batch, dim=0)  # [nh]
        self.v_bias.grad = -torch.mean(v_batch, dim=0)  # [nv]

        # Gibbs sampling
        if pcd == True: # PCD
            self.persistent_v = self.persistent_v.detach()
            v_sample = self.forward(self.persistent_v, mc, k, epsilon)  # [batch_size, nv]
            self.persistent_v = v_sample.detach().clone()           
        else: # CD
            v_sample = self.forward(v_batch, mc, k, epsilon)  # [batch_size, nv]

        p_h_sample= torch.sigmoid(self.xi(v_sample))  # [batch_size, nh]

        # data term - model term
        self.W.grad -= -torch.matmul(p_h_sample.t(), v_sample)/v_sample.size(0)  # [nh, nv]
        self.h_bias.grad -= -torch.mean(p_h_sample, dim=0)  # [nh]
        self.v_bias.grad -= -torch.mean(v_sample, dim=0)  # [nv]

        # Update parameters manually by gradient descent
        for param in [self.W, self.v_bias, self.h_bias]:
            param.data -= lr * param.grad

        # self.W.data.clamp_(-3, 5)

        E_data = torch.mean(self.visible_energy(v_batch))
        E_model = torch.mean(self.visible_energy(v_sample))       
        E_diff = E_model - E_data 
        # loss = nn.MSELoss(reduction='mean') 
        # MSE = loss(v_sample, v_batch) 

        # v_recon = self.forward(v_batch, mc='gibbs', k=1)
        # MSE = torch.mean((v_recon - v_batch)**2)

        logits = self.omega(self.v_to_h(v_batch))  # [batch_size, nv*C]
        CE = F.cross_entropy(logits.view(-1, self.n_class), v_batch.view(-1, self.n_class))  # [batch_size*nv, C] -> 1

        return E_data, E_model, E_diff, CE





def train(model, train_loader, pcd, mc, k, epsilon, lr, n_epochs):
    if pcd == True:
        print(f"Training with PCD and {k}-step {mc} updates")
    else:
        print(f"Training with CD and {k}-step {mc} updates")

    history = {"E_data": [], "E_model": [], "E_diff": [], "CE": []}

    for epoch in range(n_epochs):
        E_data_epoch, E_model_epoch, E_diff_epoch, ce_epoch = 0., 0., 0., 0.
        for batch, (X_train, _) in enumerate(train_loader):
            X_train = X_train.to(device)
            E_data, E_model, E_diff, ce = model.contrastive_divergence(X_train, pcd, mc, k, epsilon, lr)
            E_data_epoch += E_data.item()
            E_model_epoch += E_model.item()
            E_diff_epoch += E_diff.item()
            ce_epoch += ce.item()

        E_data_epoch /= len(train_loader)
        E_model_epoch /= len(train_loader)
        E_diff_epoch /= len(train_loader)
        ce_epoch /= len(train_loader)

        history["E_data"].append(E_data_epoch)
        history["E_model"].append(E_model_epoch)

        history["E_diff"].append(E_diff_epoch)
        history["CE"].append(ce_epoch)

        print(f"Epoch {epoch + 1}/{n_epochs}, E_data: {E_data_epoch:.4f}, E_model: {E_model_epoch:.4f}, E_diff: {E_diff_epoch:.4f}, CE: {ce_epoch:.4f}")

    return history


def main():
    T = sys.argv[1]
    T = float(T)
    q = 2
    L = 32
    Tc = 1.0 / np.log(1.0 + np.sqrt(q))
    print('q =', q, 'and Tc =', Tc)

    path = './2dPotts_L32/'
    filename = os.path.join(path, "potts_configs_q2L32T{:.3f}.npy".format(T))
    configs = np.load(filename)
    print(configs.shape)

    # preprocess dataset
    transform = transforms.Compose([
        OneHotTransform(q),
        transforms.Lambda(lambda x: x.view(-1)),  # Flatten  
    ])

    dataset = PottsDataset(npy_path=filename, q=q, transform=transform)

    #dataset_size = len(dataset)
    #train_size = int(0.8 * dataset_size)
    #test_size  = dataset_size - train_size
    #train_dataset, test_dataset = random_split(dataset, [train_size, test_size])  # split 80:20
    #print('train_size: ', train_size, 'test_size: ', test_size)

    train_dataset = dataset
    print('train_size:', len(train_dataset))

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    #test_loader = DataLoader(test_dataset, batch_size=64, shuffle=True)
    X_batch, y_batch = next(iter(train_loader))
    print(X_batch.shape)

    # define RBM model
    C = q
    n_visible = L*L  # e.g. 16x16 or 32x32
    n_hidden = 512  # hidden units
    mf = False  # mean-field v or not
    rbm = RBM_multinomial(C, n_visible, n_hidden, mf).to(device)

    # define training hyperparameters
    n_epochs = 500
    lr = 0.01
    k = 10
    pcd = False
    mc = 'gibbs'  # gibbs or langevin
    epsilon = 0.05  # langevin step size
    cdtype = 'pcd' if pcd else 'cd'

    history = train(rbm, train_loader, pcd, mc, k, epsilon, lr, n_epochs)

    # Generate starting from a random pixel distribution or a random hidden unit distribution.
    # Commented out lines are for different initializations.
    n_sample = 20000
    ph = 0.5  # Bernoulli probability
    h0 = torch.bernoulli(torch.ones(n_sample, n_hidden)*ph).float().to(device)  # bernoulli 0,1 with probability ph
    X0 = rbm.h_to_v(h0)
    # X0 = torch.randint(1, (n_sample, n_visible),requires_grad=False).float().to(device)  # binary 0,1
    # X0 = torch.rand((n_sample, n_visible),requires_grad=False).float().to(device)  # uniform [0,1]

    # Use Gibbs sampling for generation
    with torch.no_grad():  # no graph, avoid GPU memory growth
        X_gen = rbm.forward(X0, mc='gibbs', k=1000, epsilon=0.01).detach()  # gibbs or manual diff langevin does not need graph
    # X_gen is in one-hot encoding

    X_cat = X_gen.view(-1,n_visible,C).argmax(dim=-1) # categorical X
    path = './q2L32_gen/'
    filename = os.path.join(path, "gen_configs_q2L32T{:.3f}.npy".format(T))
    np.save(filename, X_cat.detach().cpu().numpy())

if __name__ == "__main__":
    main()
