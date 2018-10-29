from __future__ import division
from collections import OrderedDict
import argparse
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from torch.autograd import Variable
import sys
sys.path.append('../')
from net2net import wider, deeper
import copy
import numpy as np

from utils import NLL_loss_instance
from utils import PlotLearning


# Training settings
parser = argparse.ArgumentParser(description='PyTorch MNIST Example')
parser.add_argument('--batch-size', type=int, default=64, metavar='N',
                    help='input batch size for training (default: 64)')
parser.add_argument('--test-batch-size', type=int, default=1000, metavar='N',
                    help='input batch size for testing (default: 1000)')
parser.add_argument('--epochs', type=int, default=10, metavar='N',
                    help='number of epochs to train (default: 10)')
parser.add_argument('--lr', type=float, default=0.01, metavar='LR',
                    help='learning rate (default: 0.01)')
parser.add_argument('--momentum', type=float, default=0.9, metavar='M',
                    help='SGD momentum (default: 0.9)')
parser.add_argument('--no-cuda', action='store_true', default=False,
                    help='disables CUDA training')
parser.add_argument('--seed', type=int, default=1, metavar='S',
                    help='random seed (default: 1)')
parser.add_argument('--log-interval', type=int, default=1000, metavar='N',
                    help='how many batches to wait before logging status')
parser.add_argument('--noise', type=int, default=1,
                    help='noise or no noise 0-1')
parser.add_argument('--weight_norm', type=int, default=1,
                    help='norm or no weight norm 0-1')
args = parser.parse_args()
args.cuda = not args.no_cuda and torch.cuda.is_available()

torch.manual_seed(args.seed)
if args.cuda:
    torch.cuda.manual_seed(args.seed)

train_transform = transforms.Compose(
             [
              transforms.ToTensor(),
              transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])

test_transform = transforms.Compose(
             [transforms.ToTensor(),
              transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])


kwargs = {'num_workers': 8, 'pin_memory': True} if args.cuda else {}
train_loader = torch.utils.data.DataLoader(
    datasets.CIFAR10('./data', train=True, download=True, transform=train_transform),
    batch_size=args.batch_size, shuffle=True, **kwargs)
test_loader = torch.utils.data.DataLoader(
    datasets.CIFAR10('./data', train=False, transform=test_transform),
    batch_size=args.test_batch_size, shuffle=True, **kwargs)


class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(3, 8, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(8)
        self.pool1 = nn.MaxPool2d(3, 2)
        self.conv2 = nn.Conv2d(8, 16, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(16)
        self.pool2 = nn.MaxPool2d(3, 2)
        self.conv3 = nn.Conv2d(16, 32, 3, padding=1)
        self.bn3 = nn.BatchNorm2d(32)
        self.pool3 = nn.AvgPool2d(5, 1)
        self.fc1 = nn.Linear(32 * 3 * 3, 10)
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, np.sqrt(2. / n))
                m.bias.data.fill_(0.0)
            if isinstance(m, nn.Linear):
                m.bias.data.fill_(0.0)

    def forward(self, x):
        try:
            x = self.conv1(x)
            x = self.bn1(x)
            x = F.relu(x)
            x = self.pool1(x)
            x = self.conv2(x)
            x = self.bn2(x)
            x = F.relu(x)
            x = self.pool2(x)
            x = self.conv3(x)
            x = self.bn3(x)
            x = F.relu(x)
            x = self.pool3(x)
            x = x.view(-1, x.size(1) * x.size(2) * x.size(3))
            x = self.fc1(x)
            return F.log_softmax(x, dim=1)
        except RuntimeError:
            print(x.size())

    def net2net_wider(self):
        self.conv1, self.conv2, _ = wider(self.conv1, self.conv2, 12,
                                          self.bn1, noise=args.noise)
        self.conv2, self.conv3, _ = wider(self.conv2, self.conv3, 24,
                                          self.bn2, noise=args.noise)
        self.conv3, self.fc1, _ = wider(self.conv3, self.fc1, 48,
                                        self.bn3, noise=args.noise)
        print(self)

    def net2net_deeper(self):
        s = deeper(self.conv1, nn.ReLU, bnorm_flag=True, weight_norm=args.weight_norm, noise=args.noise)
        self.conv1 = s
        s = deeper(self.conv2, nn.ReLU, bnorm_flag=True, weight_norm=args.weight_norm, noise=args.noise)
        self.conv2 = s
        s = deeper(self.conv3, nn.ReLU, bnorm_flag=True, weight_norm=args.weight_norm, noise=args.noise)
        self.conv3 = s
        print(self)

    def net2net_deeper_nononline(self):
        s = deeper(self.conv1, None, bnorm_flag=True, weight_norm=args.weight_norm, noise=args.noise)
        self.conv1 = s
        s = deeper(self.conv2, None, bnorm_flag=True, weight_norm=args.weight_norm, noise=args.noise)
        self.conv2 = s
        s = deeper(self.conv3, None, bnorm_flag=True, weight_norm=args.weight_norm, noise=args.noise)
        self.conv3 = s
        print(self)

    def define_wider(self):
        self.conv1 = nn.Conv2d(3, 12, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(12)
        self.conv2 = nn.Conv2d(12, 24, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(24)
        self.conv3 = nn.Conv2d(24, 48, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(48)
        self.fc1 = nn.Linear(48*3*3, 10)

    def define_wider_deeper(self):
        self.conv1 = nn.Sequential(nn.Conv2d(3, 12, kernel_size=3, padding=1),
                                   nn.BatchNorm2d(12),
                                   nn.ReLU(),
                                   nn.Conv2d(12, 12, kernel_size=3, padding=1))
        self.bn1 = nn.BatchNorm2d(12)
        self.conv2 = nn.Sequential(nn.Conv2d(12, 24, kernel_size=3, padding=1),
                                   nn.BatchNorm2d(24),
                                   nn.ReLU(),
                                   nn.Conv2d(24, 24, kernel_size=3, padding=1))
        self.bn2 = nn.BatchNorm2d(24)
        self.conv3 = nn.Sequential(nn.Conv2d(24, 48, kernel_size=3, padding=1),
                                   nn.BatchNorm2d(48),
                                   nn.ReLU(),
                                   nn.Conv2d(48, 48, kernel_size=3, padding=1))
        self.bn3 = nn.BatchNorm2d(48)
        self.fc1 = nn.Linear(48*3*3, 10)
        print(self)


def net2net_deeper_recursive(model):
    """
    Apply deeper operator recursively any conv layer.
    """
    for name, module in model._modules.items():
        if isinstance(module, nn.Conv2d):
            s = deeper(module, nn.ReLU, bnorm_flag=False)
            model._modules[name] = s
        elif isinstance(module, nn.Sequential):
            module = net2net_deeper_recursive(module)
            model._modules[name] = module
    return model


def train(model, epoch):
    model.train()
    avg_loss = 0
    avg_accu = 0
    for batch_idx, (data, target) in enumerate(train_loader):
        if args.cuda:
            data, target = data.cuda(), target.cuda()
        data, target = Variable(data), Variable(target)
        optimizer.zero_grad()
        output = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        pred = output.data.max(1, keepdim=True)[1]  # get the index of the max log-probability
        avg_accu += pred.eq(target.data.view_as(pred)).cpu().sum()
        avg_loss += loss.item()
        if batch_idx % args.log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader), loss.item()))
    avg_loss /= batch_idx + 1
    avg_accu = avg_accu.item() / len(train_loader.dataset)
    return avg_accu, avg_loss


def test(model):
    model.eval()
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in test_loader:
            if args.cuda:
                data, target = data.cuda(), target.cuda()
            data, target = Variable(data), Variable(target)
            output = model(data)
            test_loss += F.nll_loss(output, target).item()  # sum up batch loss
            pred = output.data.max(1, keepdim=True)[1]  # get the index of the max log-probability
            correct += pred.eq(target.data.view_as(pred)).cpu().sum()

    test_loss /= len(test_loader.dataset)
    print('\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.2f}%)\n'.format(
        test_loss, correct, len(test_loader.dataset),
        100. * float(correct) / len(test_loader.dataset)))

    return correct.item() / len(test_loader.dataset), test_loss


def run_training(model, run_name, epochs, plot=None, lr=args.lr, bt=None):
    global optimizer
    best_test = {"epoch": 0, "test_accuracy": 0.0, "validation_accuarcy": 0.00}
    acc = OrderedDict([('epoch1', 0), ('test_accuracy1', 0.0), ('epoch2', 0), ('test_accuracy2', 0.0)])
    model.cuda()
    optimizer = optim.SGD(model.parameters(), lr=lr, momentum=args.momentum)
    if plot is None:
        plot = PlotLearning('./plots/cifar/', 10, prefix=run_name)
    flag = False
    for epoch in range(1, epochs + 1):
        accu_train, loss_train = train(model, epoch)
        accu_test, loss_test = test(model)
        logs = {}
        logs['acc'] = accu_train
        logs['val_acc'] = accu_test
        logs['loss'] = loss_train
        logs['val_loss'] = loss_test
        plot.plot(logs)

        if bt is not None:
            if accu_test > bt['test_accuracy'] and flag is False:
                acc['epoch1'] = bt['epoch']
                acc['test_accuracy1'] = bt['test_accuracy']
                acc['epoch2'] = epoch
                acc['test_accuracy2'] = accu_test
                flag = True

        if accu_test > best_test["test_accuracy"]:
            best_test["epoch"] = epoch
            best_test["test_accuracy"] = accu_test
            best_test["validation_accuarcy"] = accu_train

    print "========================================="
    print "the epoch with best test accuracy is:",
    print best_test
    print "the accuracy reached with net2net in"
    print acc
    print "========================================="
    return plot, best_test


if __name__ == "__main__":
    start_t = time.time()
    print("\n\n > Teacher training ... ")
    model = Net()
    model.cuda()
    criterion = nn.NLLLoss()
    plot, _ = run_training(model, 'Teacher_', args.epochs)

    # wider teacher training
    start_t = time.time()
    print("\n\n > Wider teacher training (from scratch)... ")
    model_t1 = Net()

    model_t1.define_wider()
    model_t1.cuda()
    plot, bt1 = run_training(model_t1, 'Wider_teacher_', args.epochs)
    print(" >> Time taken for training wider network from scratch {}".format(time.time() - start_t))

    # wider student training
    start_t = time.time()
    print("\n\n > Wider Student training ... ")
    model_ = Net()
    model_ = copy.deepcopy(model)

    del model
    model = model_
    model.net2net_wider()
    plot, bt2 = run_training(model, 'Wider_student_', args.epochs, plot, args.lr, bt1)
    print(" >> Time taken for training wider network via net2net {}".format(time.time() - start_t))



    # wider + deeper student training
    # print("\n\n > Wider+Deeper Student training ... ")
    # model_ = Net()
    # model_.net2net_wider()
    # model_ = copy.deepcopy(model)
    #
    # del model
    # model = model_
    # model.net2net_deeper_nononline()
    # run_training(model, 'WiderDeeper_student_', (args.epochs + 1) // 3, plot)

    # wider deeper teacher training
    # print("\n\n > Wider+Deeper teacher training ... ")
    # start_t = time.time()
    # model_ = Net()
    #
    # del model
    # model = model_
    # model.define_wider_deeper()
    # run_training(model, 'Wider_Deeper_teacher_', args.epochs + 1)
    # print(" >> Time taken  {}".format(time.time() - start_t))