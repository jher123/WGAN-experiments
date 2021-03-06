# The definition of the basic Wasserstein GAN which generates 64x64 or 128x128 images
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.utils as vutils


class DeconvBlock(nn.Module):
    def __init__(self, n_in, n_out, ks, stride, pad, bn=True):
        super().__init__()
        self.conv = nn.ConvTranspose2d(n_in, n_out, ks, stride, padding=pad, bias=False)
        self.bn = nn.BatchNorm2d(n_out)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        x = self.relu(self.conv(x))
        return self.bn(x) if self.bn else x


def conv_block(n_in, n_out, ks, stride, pad=None, bn=True):
    if pad is None:
        pad = ks//2//stride
    if bn == True:
        res = nn.Sequential(
            nn.Conv2d(n_in, n_out, kernel_size=ks, bias=False, stride=stride, padding=pad),
            nn.BatchNorm2d(n_out),
            nn.LeakyReLU(negative_slope=0.2, inplace=True)
        )
    else:
        res = nn.Sequential(
            nn.Conv2d(n_in, n_out, kernel_size=ks, bias=False, stride=stride, padding=pad),
            nn.LeakyReLU(negative_slope=0.2, inplace=True)
        )
    return res

class Discriminator(nn.Module):
    def __init__(self, im_size, ks, ndf, nc=3, ngpu=1):
        super().__init__()
        self.ngpu = ngpu
        self.im_size = im_size
        self.main64 = nn.Sequential(
            # input: nc x 64 x 64
            conv_block(nc, ndf, ks, 2, 1, bn=False),
            # ndf x 32 x 32
            conv_block(ndf, ndf*2, ks, 2, 1),
            # ndf*2 x 16 x 16
            conv_block(ndf*2, ndf*4, ks, 2, 1),
            # ndf*4 x 8 x 8
            conv_block(ndf*4, ndf*8, ks, 2, 1),
            # ndf*8 x 4 x 4
            # the last cov has 1 channel and a grid size of no more than 4x4. So we are going to spit out 4x4x1 tensor
            nn.Conv2d(ndf*8, 1, ks, 1, 0, bias=False)
        )
        self.main128 = nn.Sequential(
            # input: nc x 128 x 128
            conv_block(nc, ndf, ks, 2, 1, bn=False),
            # conv2: ndf x 64 x 64
            conv_block(ndf, ndf*2, ks, 2, 1), # 64, 12
            # conv3: ndf*2 x 32 x 32
            conv_block(ndf*2, ndf*4, ks, 2, 1), # 128, 256
            # conv4: ndf*4 x 16 x 16
            conv_block(ndf*4, ndf*8, ks, 2, 1), # 256,  512
            # conv5: ndf*8 x 8 x 8
            conv_block(ndf*8, ndf*16, ks, 2, 1), # 512, 1024
            # the last cov has 1 channel and a grid size of no more than 4x4. So we are going to spit out 4x4x1 tensor
            nn.Conv2d(ndf*16, 1, ks, 1, 0, bias=False)
        )

    def forward(self, input):
        if self.im_size == 64:
            return self.main64(input).mean(0).view(1)
        else:
            return self.main128(input).mean(0).view(1)


class Generator(nn.Module):
    def __init__(self, im_size, ks, nz, ngf, nc=3, ngpu=1):
        super().__init__()
        self.ngpu = ngpu
        self.im_size = im_size
        self.main64 = nn.Sequential(
            # input z going into convolution
            DeconvBlock(nz, ngf*8, ks, 1, 0),
            # ngf*8 x 4 x 4
            DeconvBlock(ngf*8, ngf*4, ks, 2, 1),
            # ngf*4 (256) x 8 x 8
            DeconvBlock(ngf*4, ngf*2, ks, 2, 1),
            # ngf*2 x 16 x 16
            DeconvBlock(ngf*2, ngf, ks, 2, 1),
            # ngf x 32 x 32
            nn.ConvTranspose2d(ngf, nc, ks, 2, 1, bias=False),
            nn.Tanh()
            # output: nc x 64 x 64
        )
        self.main128 = nn.Sequential(
            # input z going into convolution
            DeconvBlock(nz, ngf*16, ks, 1, 0),
            # ngf*16 x 4 x 4
            DeconvBlock(ngf*16, ngf*8, ks, 2, 1),
            # ngf*8 (256) x 8 x 8
            DeconvBlock(ngf*8, ngf*4, ks, 2, 1),
            # ngf*4 x 16 x 16
            DeconvBlock(ngf*4, ngf*2, ks, 2, 1),
            # ngf*2 x 32 x 32
            DeconvBlock(ngf*2, ngf, ks, 2, 1),
            # ngf x 64 x 64 - optional for 128 x128 ims
            nn.ConvTranspose2d(ngf, nc, ks, 2, 1, bias=False),
            nn.Tanh()
            # output: nc x 128 x 128
        )
    def forward(self, input):
        if self.im_size == 64:
            return self.main64(input)
        else:
            return self.main128(input)
