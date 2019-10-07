#AUTOGENERATED! DO NOT EDIT! File to edit: dev/19_callback_mixup.ipynb (unless otherwise specified).

__all__ = ['reduce_loss', 'MixUp']

#Cell
from ..torch_basics import *
from ..test import *
from ..layers import *
from ..data.all import *
from ..optimizer import *
from ..learner import *
from .progress import *
from ..vision.core import *

#Cell
def reduce_loss(loss, reduction='mean'):
    return loss.mean() if reduction=='mean' else loss.sum() if reduction=='sum' else loss

#Cell
from torch.distributions.beta import Beta

class MixUp(Callback):
    run_after=[Normalize, Cuda]
    def __init__(self, alpha=0.4): self.distrib = Beta(tensor([alpha]), tensor([alpha]))

    def begin_fit(self): self.old_loss_func,self.learn.loss_func = self.learn.loss_func,self.loss_func

    def begin_batch(self):
        if not self.training: return #Only mixup things during training
        lam = self.distrib.sample((self.y.size(0),)).squeeze().to(self.x.device)
        lam = torch.stack([lam, 1-lam], 1)
        self.lam = lam.max(1)[0][:,None,None,None]
        shuffle = torch.randperm(self.y.size(0)).to(self.x.device)
        xb1,self.yb1 = tuple(x[shuffle] for x in self.xb),tuple(y[shuffle] for y in self.yb)
        self.learn.xb = tuple(torch.lerp(x1, x, self.lam) for x,x1 in zip(self.xb, xb1))

    def after_fit(self): self.run.loss_func = self.old_loss_func

    def loss_func(self, pred, *yb):
        if not self.in_train: return self.old_loss_func(pred, *yb)
        with NoneReduce(self.old_loss_func) as loss_func:
            loss1 = loss_func(pred, *yb)
            loss2 = loss_func(pred, *self.yb1)
        loss = torch.lerp(loss2, loss1, self.lam)
        return reduce_loss(loss, getattr(self.old_loss_func, 'reduction', 'mean'))