import os
import torch as th
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pylab as plt
from visdom import Visdom

class NLL_loss_instance(th.nn.NLLLoss):

    def __init__(self, ratio):
        super(NLL_loss_instance, self).__init__(None, True)
        self.ratio = ratio

    def forward(self, x, y, ratio=None):
        if ratio is not None:
            self.ratio = ratio
        num_inst = x.size(0)
        num_hns = int(self.ratio * num_inst)
        x_ = x.clone()
        for idx, label in enumerate(y.data):
            x_.data[idx, label] = 0.0
        loss_incs = -x_.sum(1)
        _, idxs = loss_incs.topk(num_hns)
        x_hn = x.index_select(0, idxs)
        y_hn = y.index_select(0, idxs)
        return th.nn.functional.nll_loss(x_hn, y_hn)


class PlotLearning(object):

    def __init__(self, save_path, num_classes, prefix='', plot_name=''):
        self.DEFAULT_PORT = 9898
        self.DEFAULT_HOSTNAME = 'http://130.83.143.241'
        self.accuracy = []
        self.val_accuracy = []
        self.losses = []
        self.val_losses = []
        self.save_path_loss = os.path.join(save_path, prefix + 'loss_plot.png')
        self.save_path_accu = os.path.join(save_path, prefix + 'accu_plot.png')
        self.init_loss = -np.log(1.0 / num_classes)
        self.viz = Visdom(port=self.DEFAULT_PORT, server=self.DEFAULT_HOSTNAME)
        self.plot_name = plot_name

    def plot(self, logs):
        self.accuracy.append(logs.get('acc'))
        self.val_accuracy.append(logs.get('val_acc'))
        self.losses.append(logs.get('loss'))
        self.val_losses.append(logs.get('val_loss'))

        best_val_acc = max(self.val_accuracy)
        best_train_acc = max(self.accuracy)
        best_val_epoch = self.val_accuracy.index(best_val_acc)
        best_train_epoch = self.accuracy.index(best_train_acc)

        plt.figure(1)
        plt.gca().cla()
        plt.ylim(0, 1)
        plt.plot(self.accuracy, label='train')
        plt.plot(self.val_accuracy, label='valid')
        plt.title("best_val@{0:}-{1:.2f}, best_train@{2:}-{3:.2f}".format(
            best_val_epoch, best_val_acc, best_train_epoch, best_train_acc))
        plt.legend()
        plt.savefig(self.save_path_accu)

        best_val_loss = min(self.val_losses)
        best_train_loss = min(self.losses)
        best_val_epoch = self.val_losses.index(best_val_loss)
        best_train_epoch = self.losses.index(best_train_loss)

        plt.figure(2)
        plt.gca().cla()
        plt.ylim(0, self.init_loss)
        plt.plot(self.losses, label='train')
        plt.plot(self.val_losses, label='valid')
        plt.title("best_val@{0:}-{1:.2f}, best_train@{2:}-{3:.2f}".format(
            best_val_epoch, best_val_loss, best_train_epoch, best_train_loss))
        plt.legend()
        plt.savefig(self.save_path_loss)

    def plot_logs(self, logs, plot_name):

        # plt.figure()
        # plt.ylim(0, 1)
        # plt.ylabel("Accuracy")
        # plt.xlabel("epochs")
        # plt.plot(logs[0]['epoch'], logs[0]['train_accuracy'], 'r--', label='base')
        # plt.plot(logs[0]['epoch'], logs[0]['test_accuracy'], 'r')
        # plt.plot(logs[1]['epoch'], logs[1]['train_accuracy'], 'g--', label='wider_scratch')
        # plt.plot(logs[1]['epoch'], logs[1]['test_accuracy'], 'g')
        # plt.plot(logs[2]['epoch'], logs[2]['train_accuracy'], 'y--', label='net2net')
        # plt.plot(logs[2]['epoch'], logs[2]['test_accuracy'], 'y')
        # plt.legend()
        # plt.savefig(self.save_path_accu)
        #
        # plt.figure()
        # plt.ylim(0, self.init_loss)
        # plt.ylabel("Loss")
        # plt.xlabel("epochs")
        # plt.plot(logs[0]['epoch'], logs[0]['train_loss'], 'r--')
        # plt.plot(logs[0]['epoch'], logs[0]['test_loss'], 'r')
        # plt.plot(logs[1]['epoch'], logs[1]['train_loss'], 'g--')
        # plt.plot(logs[1]['epoch'], logs[1]['test_loss'], 'g')
        # plt.plot(logs[2]['epoch'], logs[2]['train_loss'], 'y--')
        # plt.plot(logs[2]['epoch'], logs[2]['test_loss'], 'y')
        # plt.legend()
        # plt.savefig(self.save_path_loss)



        trace1 = dict(x=logs[0]['epoch'], y=logs[0]['train_accuracy'], mode="lines", type='custom',
                      line={'color': 'blue', 'dash': 'dash'}, name='Base Train Accuracy')
        trace2 = dict(x=logs[0]['epoch'], y=logs[0]['test_accuracy'], mode="lines", type='custom',
                      line={'color': 'blue', 'shape': 'spline', 'smoothing': 1.3}, name='Base Test Accuracy')
        trace3 = dict(x=logs[1]['epoch'], y=logs[1]['train_accuracy'], mode="lines", type='custom',
                      line={'color': 'green','dash': 'dash'}, name='Wider/Deeper Train Accuracy')
        trace4 = dict(x=logs[1]['epoch'], y=logs[1]['test_accuracy'], mode="lines", type='custom',
                      line={'color': 'green', 'shape': 'spline', 'smoothing': 1.3}, name='Wider/Deeper Test Accuracy')
        trace5 = dict(x=logs[2]['epoch'], y=logs[2]['train_accuracy'], mode="lines", type='custom',
                      line={'color': 'red', 'dash': 'dash'}, name='Wider/Deeper Net2Net Train Accuracy')
        trace6 = dict(x=logs[2]['epoch'], y=logs[2]['test_accuracy'], mode="lines", type='custom',
                      line={'color': 'red', 'shape': 'spline', 'smoothing': 1.3}, name='Wider/Deeper Net2Net Test Accuracy')
        layout = dict(title="Accuracy Vs Epoch - " + plot_name, xaxis={'title': 'Epochs'}, yaxis={'title': 'Accuracy'})
        self.viz._send({'data': [trace1, trace2, trace3, trace4, trace5, trace6],
                        'layout': layout, 'win': 'Accuracy' + self.plot_name})

        trace1 = dict(x=logs[0]['epoch'], y=logs[0]['train_loss'], mode="lines", type='custom',
                      line={'color': 'blue', 'dash': 'dash'}, name='Base Train Loss')
        trace2 = dict(x=logs[0]['epoch'], y=logs[0]['test_loss'], mode="lines", type='custom',
                      line={'color': 'blue', 'shape': 'spline', 'smoothing': 1.3}, name='Base Test loss')
        trace3 = dict(x=logs[1]['epoch'], y=logs[1]['train_loss'], mode="lines", type='custom',
                      line={'color': 'green', 'dash': 'dash'}, name='Wider Train Loss')
        trace4 = dict(x=logs[1]['epoch'], y=logs[1]['test_loss'], mode="lines", type='custom',
                      line={'color': 'green', 'shape': 'spline', 'smoothing': 1.3}, name='Wider/Deeper Test loss')
        trace5 = dict(x=logs[2]['epoch'], y=logs[2]['train_loss'], mode="lines", type='custom',
                      line={'color': 'red', 'dash': 'dash'}, name='Wider Net2Net Train Loss')
        trace6 = dict(x=logs[2]['epoch'], y=logs[2]['test_loss'], mode="lines", type='custom',
                      line={'color': 'red', 'shape': 'spline', 'smoothing': 1.3}, name='Wider/Deeper Net2Net Test loss')
        layout = dict(title="Loss Vs Epoch - " + plot_name, xaxis={'title': 'Epochs'}, yaxis={'title': 'Loss'})
        self.viz._send({'data': [trace1, trace2, trace3, trace4, trace5, trace6],
                        'layout': layout, 'win': 'Model_' + self.plot_name})



