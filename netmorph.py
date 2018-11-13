import torch as th
import numpy as np

NOISE_RATIO = 1e-5
ERROR_TOLERANCE = 1e-3


def add_noise(weights, other_weights):
    noise_range = NOISE_RATIO * np.ptp(other_weights.flatten())
    noise = th.cuda.FloatTensor(weights.shape).uniform_(-noise_range / 2.0, noise_range / 2.0)

    return th.add(noise, weights)


def verify_TH(teacher_w1, teacher_b1, teacher_w2, student_w1, student_b1, student_w2):
    import scipy.signal
    inputs = np.random.rand(teacher_w1.shape[1], teacher_w1.shape[3] * 4, teacher_w1.shape[2] * 4)
    ori1 = np.zeros((teacher_w1.shape[0], teacher_w1.shape[3] * 4, teacher_w1.shape[2] * 4))
    ori2 = np.zeros((teacher_w2.shape[0], teacher_w1.shape[3] * 4, teacher_w1.shape[2] * 4))
    new1 = np.zeros((student_w1.shape[0], teacher_w1.shape[3] * 4, teacher_w1.shape[2] * 4))
    new2 = np.zeros((student_w2.shape[0], teacher_w1.shape[3] * 4, teacher_w1.shape[2] * 4))

    # print "input shape:" + str(inputs.shape)
    # print "orig 1 shape:" + str(ori1.shape)
    # print "orig 2 shape:" + str(ori2.shape)
    # print 'new1 shape' + str(new1.shape)
    # print 'new2 shape' + str(new2.shape)
    # print 'teacher 1 shape' + str(teacher_w1.shape)
    # print 'teacher 2 shape' + str(teacher_w2.shape)
    # print 'student 1 shape' + str(student_w1.shape)
    # print 'student 2 shape' + str(student_w2.shape)

    for i in range(teacher_w1.shape[0]):
        for j in range(inputs.shape[0]):
            if j == 0:
                tmp = scipy.signal.convolve2d(inputs[j, :, :], teacher_w1[i, j, :, :], mode='same')
            else:
                tmp += scipy.signal.convolve2d(inputs[j, :, :], teacher_w1[i, j, :, :], mode='same')
        ori1[i, :, :] = tmp + teacher_b1[i]
    for i in range(teacher_w2.shape[0]):
        for j in range(ori1.shape[0]):
            if j == 0:
                tmp = scipy.signal.convolve2d(ori1[j, :, :], teacher_w2[i, j, :, :], mode='same')
            else:
                tmp += scipy.signal.convolve2d(ori1[j, :, :], teacher_w2[i, j, :, :], mode='same')
        ori2[i, :, :] = tmp

    for i in range(student_w1.shape[0]):
        for j in range(inputs.shape[0]):
            if j == 0:
                tmp = scipy.signal.convolve2d(inputs[j, :, :], student_w1[i, j, :, :], mode='same')
            else:
                tmp += scipy.signal.convolve2d(inputs[j, :, :], student_w1[i, j, :, :], mode='same')
        new1[i, :, :] = tmp + student_b1[i]
    for i in range(student_w2.shape[0]):
        for j in range(new1.shape[0]):
            if j == 0:
                tmp = scipy.signal.convolve2d(new1[j, :, :], student_w2[i, j, :, :], mode='same')
            else:
                tmp += scipy.signal.convolve2d(new1[j, :, :], student_w2[i, j, :, :], mode='same')
        new2[i, :, :] = tmp

    err = np.abs(np.sum(ori2 - new2))

    assert err < ERROR_TOLERANCE, 'Verification failed: [ERROR] {}'.format(err)


def verify_TF(teacher_w1, teacher_b1, teacher_w2, student_w1, student_b1, student_w2):
    import scipy.signal
    inputs = np.random.rand(teacher_w1.shape[0] * 4, teacher_w1.shape[1] * 4, teacher_w1.shape[2])
    ori1 = np.zeros((teacher_w1.shape[0] * 4, teacher_w1.shape[1] * 4, teacher_w1.shape[3]))
    ori2 = np.zeros((teacher_w1.shape[0] * 4, teacher_w1.shape[1] * 4, teacher_w2.shape[3]))
    new1 = np.zeros((teacher_w1.shape[0] * 4, teacher_w1.shape[1] * 4, student_w1.shape[3]))
    new2 = np.zeros((teacher_w1.shape[0] * 4, teacher_w1.shape[1] * 4, student_w2.shape[3]))

    for i in range(teacher_w1.shape[3]):
        for j in range(inputs.shape[2]):
            if j == 0:
                tmp = scipy.signal.convolve2d(inputs[:, :, j], teacher_w1[:, :, j, i], mode='same')
            else:
                tmp += scipy.signal.convolve2d(inputs[:, :, j], teacher_w1[:, :, j, i], mode='same')
        ori1[:, :, i] = tmp + teacher_b1[i]

    for i in range(teacher_w2.shape[3]):
        for j in range(ori1.shape[2]):
            if j == 0:
                tmp = scipy.signal.convolve2d(ori1[:, :, j], teacher_w2[:, :, j, i], mode='same')
            else:
                tmp += scipy.signal.convolve2d(ori1[:, :, j], teacher_w2[:, :, j, i], mode='same')
        ori2[:, :, i] = tmp

    for i in range(student_w1.shape[3]):
        for j in range(inputs.shape[2]):
            if j == 0:
                tmp = scipy.signal.convolve2d(inputs[:, :, j], student_w1[:, :, j, i], mode='same')
            else:
                tmp += scipy.signal.convolve2d(inputs[:, :, j], student_w1[:, :, j, i], mode='same')
        new1[:, :, i] = tmp + student_b1[i]

    for i in range(student_w2.shape[3]):
        for j in range(new1.shape[2]):
            if j == 0:
                tmp = scipy.signal.convolve2d(new1[:, :, j], student_w2[:, :, j, i], mode='same')
            else:
                tmp += scipy.signal.convolve2d(new1[:, :, j], student_w2[:, :, j, i], mode='same')
        new2[:, :, i] = tmp

    err = np.abs(np.sum(ori2 - new2))

    assert err < ERROR_TOLERANCE, 'Verification failed: [ERROR] {}'.format(err)





def _wider_TF(teacher_w1, teacher_b1, teacher_w2, rand):

    replication_factor = np.bincount(rand)
    student_w1 = teacher_w1.copy()
    student_w2 = teacher_w2.copy()
    student_b1 = teacher_b1.copy()

    for i in range(len(rand)):
        teacher_index = rand[i]
        new_weight = teacher_w1[:, :, :, teacher_index]
        new_weight = new_weight[:, :, :, np.newaxis]
        student_w1 = np.concatenate((student_w1, new_weight), axis=3)
        student_b1 = np.append(student_b1, teacher_b1[teacher_index])

    for i in range(len(rand)):
        teacher_index = rand[i]
        factor = replication_factor[teacher_index] + 1
        assert factor > 1, 'Error in Net2Wider'
        new_weight = teacher_w2[:, :, teacher_index, :]*(1./factor)
        new_weight_re = new_weight[:, :, np.newaxis, :]
        student_w2 = np.concatenate((student_w2, new_weight_re), axis=2)
        student_w2[:, :, teacher_index, :] = new_weight

    # verify_TF(teacher_w1, teacher_b1, teacher_w2, student_w1, student_b1, student_w2)


def _wider_TH(w1, b1, w2, rand):

    tw1 = th.from_numpy(w1).type(th.DoubleTensor)
    tw2 = th.from_numpy(w2).type(th.DoubleTensor)
    tb1 = th.from_numpy(b1).type(th.DoubleTensor)

    sw1 = tw1.clone()
    sb1 = tb1.clone()
    sw2 = tw2.clone()

    replication_factor = np.bincount(rand)

    for i in range(rand.numel()):
        teacher_index = int(rand[i].item())
        new_weight = tw1.select(0, teacher_index)
        new_weight = new_weight.unsqueeze(0)
        sw1 = th.cat((sw1, new_weight), dim=0)
        new_bias = tb1[teacher_index].unsqueeze(0)
        sb1 = th.cat((sb1, new_bias))

    for i in range(rand.numel()):
        teacher_index = int(rand[i].item())
        factor_index = replication_factor[teacher_index] + 1
        assert factor_index > 1, 'Error in Net2Wider'
        new_weight = tw2.select(1, teacher_index) * (1. / factor_index)
        new_weight_re = new_weight.unsqueeze(1)
        sw2 = th.cat((sw2, new_weight_re), dim=1)
        sw2[:, teacher_index, :, :] = new_weight

    verify_TH(w1, b1, w2, sw1.numpy(), sb1.numpy(), sw2.numpy())


def wider(m1, m2, new_width, bnorm=None, noise=True, random_init=False, weight_norm=True):

    w1 = m1.weight.data
    w2 = m2.weight.data
    b1 = m1.bias.data

    if "Conv" in m1.__class__.__name__ and ("Conv" in m2.__class__.__name__ or "Linear" in m2.__class__.__name__):

        # Convert Linear layers to Conv if linear layer follows target layer
        if "Conv" in m1.__class__.__name__ and "Linear" in m2.__class__.__name__:
            assert w2.size(1) % w1.size(0) == 0, "Linear units need to be multiple"
            if w1.dim() == 4:
                factor = int(np.sqrt(w2.size(1) // w1.size(0)))
                w2 = w2.view(
                    w2.size(0), w2.size(1) // factor ** 2, factor, factor)
        else:
            assert w1.size(0) == w2.size(1), "Module weights are not compatible"

        assert new_width > w1.size(0), "New size should be larger"

        nw1 = w1.clone()
        nb1 = b1.clone()
        nw2 = w2.clone()

        old_width = w1.size(0)

        if bnorm is not None:
            nrunning_mean = bnorm.running_mean.clone().resize_(new_width)
            nrunning_var = bnorm.running_var.clone().resize_(new_width)
            if bnorm.affine:
                nweight = bnorm.weight.data.clone().resize_(new_width)
                nbias = bnorm.bias.data.clone().resize_(new_width)

            nrunning_var.narrow(0, 0, old_width).copy_(bnorm.running_var)
            nrunning_mean.narrow(0, 0, old_width).copy_(bnorm.running_mean)
            if bnorm.affine:
                nweight.narrow(0, 0, old_width).copy_(bnorm.weight.data)
                nbias.narrow(0, 0, old_width).copy_(bnorm.bias.data)

        rand_ids = th.randint(low=0, high=w1.shape[0], size=((new_width - w1.shape[0]),))
        replication_factor = np.bincount(rand_ids)

        for i in range(rand_ids.numel()):
            teacher_index = int(rand_ids[i].item())
            new_weight = w1.select(0, teacher_index)
            if i > 0:
                new_weight = add_noise(new_weight, nw1)
            new_weight = new_weight.unsqueeze(0)
            nw1 = th.cat((nw1, new_weight), dim=0)

            new_bias = b1[teacher_index].unsqueeze(0)
            nb1 = th.cat((nb1, new_bias))

            if bnorm is not None:
                nrunning_mean[old_width + i] = bnorm.running_mean[teacher_index]
                nrunning_var[old_width + i] = bnorm.running_var[teacher_index]
                if bnorm.affine:
                    nweight[old_width + i] = bnorm.weight.data[teacher_index]
                    nbias[old_width + i] = bnorm.bias.data[teacher_index]
                bnorm.num_features = new_width

        for i in range(rand_ids.numel()):
            teacher_index = int(rand_ids[i].item())
            factor_index = replication_factor[teacher_index] + 1
            assert factor_index > 1, 'Error in Net2Wider'
            new_weight = w2.select(1, teacher_index) * (1. / factor_index)
            new_weight_re = new_weight.unsqueeze(1)
            nw2 = th.cat((nw2, new_weight_re), dim=1)
            nw2[:, teacher_index, :, :] = new_weight

        if "Conv" in m1.__class__.__name__ and "Linear" in m2.__class__.__name__:
            m2.in_features = new_width * factor ** 2
            m2.weight.data = nw2.view(m2.weight.size(0), new_width * factor ** 2)
        else:
            m2.weight.data = nw2

        m1.weight.data = nw1
        m1.bias.data = nb1

        if bnorm is not None:
            bnorm.running_var = nrunning_var
            bnorm.running_mean = nrunning_mean
            if bnorm.affine:
                bnorm.weight.data = nweight
                bnorm.bias.data = nbias

        return m1, m2, bnorm


# TODO: Consider adding noise to new layer as wider operator.
def deeper(m, nonlin, bnorm_flag=False, weight_norm=True, noise=True):
    """
    Deeper operator adding a new layer on topf of the given layer.
    Args:
        m (module) - module to add a new layer onto.
        nonlin (module) - non-linearity to be used for the new layer.
        bnorm_flag (bool, False) - whether add a batch normalization btw.
        weight_norm (bool, True) - if True, normalize weights of m before
            adding a new layer.
        noise (bool, True) - if True, add noise to the new layer weights.
    """

    if "Linear" in m.__class__.__name__:
        m2 = th.nn.Linear(m.out_features, m.out_features)
        m2.weight.data.copy_(th.eye(m.out_features))
        m2.bias.data.zero_()

        if bnorm_flag:
            bnorm = th.nn.BatchNorm1d(m2.weight.size(1))
            bnorm.weight.data.fill_(1)
            bnorm.bias.data.fill_(0)
            bnorm.running_mean.fill_(0)
            bnorm.running_var.fill_(1)

    elif "Conv" in m.__class__.__name__:
        assert m.kernel_size[0] % 2 == 1, "Kernel size needs to be odd"

        if m.weight.dim() == 4:
            pad_h = int((m.kernel_size[0] - 1) / 2)
            # pad_w = pad_h
            m2 = th.nn.Conv2d(m.out_channels, m.out_channels,
                              kernel_size=m.kernel_size, padding=pad_h)
            m2.weight.data.zero_()
            c = m.kernel_size[0] // 2 + 1 # = 2

        restore = False
        if m2.weight.dim() == 2:
            restore = True
            m2.weight.data = m2.weight.data.view(m2.weight.size(0),
                                                 m2.in_channels,
                                                 m2.kernel_size[0],
                                                 m2.kernel_size[0])

        # if weight_norm:
        #     for i in range(m.out_channels):
        #         weight = m.weight.data
        #         norm = weight.select(0, i).norm()
        #         weight.div_(norm)
        #         m.weight.data = weight

        for i in range(0, m.out_channels):
            if m.weight.dim() == 4:
                m2.weight.data.narrow(0, i, 1).narrow(1, i, 1).narrow(2, c, 1).narrow(3, c, 1).fill_(1)

        if noise:
            noise = np.random.normal(scale=5e-2 * m2.weight.data.std(),
                                     size=list(m2.weight.size()))
            m2.weight.data += th.FloatTensor(noise).type_as(m2.weight.data)

        if restore:
            m2.weight.data = m2.weight.data.view(m2.weight.size(0),
                                                 m2.in_channels,
                                                 m2.kernel_size[0],
                                                 m2.kernel_size[0])

        m2.bias.data.zero_()

        if bnorm_flag:
            if m.weight.dim() == 4:
                bnorm = th.nn.BatchNorm2d(m2.out_channels)
            elif m.weight.dim() == 5:
                bnorm = th.nn.BatchNorm3d(m2.out_channels)
            bnorm.weight.data.fill_(1)
            bnorm.bias.data.fill_(0)
            bnorm.running_mean.fill_(0)
            bnorm.running_var.fill_(1)

    else:
        raise RuntimeError("{} Module not supported".format(m.__class__.__name__))

    s = th.nn.Sequential()
    s.add_module('conv', m)
    if bnorm_flag:
        s.add_module('bnorm', bnorm)
    if nonlin is not None:
        s.add_module('nonlin', nonlin())
    s.add_module('conv_new', m2)

    return s


if __name__ == '__main__':

    # with file('test_data_w1.txt', 'w') as test_data_w1:
    #     test_data_w1.write('# Array Shape: {0}\n'.format(w1.shape))
    #     for data_slice in w1:
    #         for slice2 in data_slice:
    #             np.savetxt(test_data_w1, slice2, fmt='%-4.8f')
    #             test_data_w1.write('# BBBB\n')
    #         test_data_w1.write('# AAAA\n')
    #
    # w1_file = np.loadtxt('test_data_w1.txt').reshape(3, 3, 2, 3)

    # for tensor flow verification
    new_width = 384
    w1 = np.random.rand(3, 3, 128, 256)
    b1 = np.random.rand(256)
    w2 = np.random.rand(3, 3, 256, 512)
    rand = np.random.randint(w1.shape[3], size=(new_width - w1.shape[3]))
    # print(rand)
    # rand = th.randint(low=0, high=tw1.shape[0], size=((new_width - tw1.shape[0]),))
    _wider_TF(w1, b1, w2, rand)

    # for torch verification
    w1 = w1.reshape(256, 128, 3, 3)
    w2 = w2.reshape(512, 256, 3, 3)
    _wider_TH(w1, b1, w2, th.from_numpy(rand))
