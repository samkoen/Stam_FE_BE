# USAGE
# python lenet_mnist.py --save-model 1 --weights output/lenet_weights.hdf5
# python lenet_mnist.py --load-model 1 --weights output/lenet_weights.hdf5

# import the necessary packages
import gc

import matplotlib.pyplot as plt
import numpy as np
from keras import optimizers
from keras.utils import to_categorical
from .lenet import LeNet
from sklearn.model_selection import train_test_split

from ocr.model import image_to_np2


def show_history(history,batch_size,epoch,opt):
    acc = history.history['acc']
    val_acc = history.history['val_acc']
    loss = history.history['loss']
    val_loss = history.history['val_loss']

    epochs = range(1,len(acc)+1)
    plt.figure()
    plt.plot(epochs,acc,'b',label='training accurarcy')
    plt.plot(epochs, val_acc, 'r', label='validation accurarcy')
    plt.title('acc epoch={}, batch={} opt={}'.format(batch_size,epoch,opt))
    plt.legend()
    plt.savefig('figure/acc_{}_{}_{}.png'.format(batch_size, epoch, opt))

    plt.figure()
    plt.plot(epochs, loss, 'b', label='training loss')
    plt.plot(epochs, val_loss, 'r', label='validation loss')
    plt.title('loss epoch={}, batch={} opt={}'.format(batch_size, epoch, opt))
    plt.legend()

    #plt.show()

    plt.savefig('figure/loss_{}_{}_{}.png'.format(batch_size, epoch, opt))


#
# # construct the argument parser and parse the arguments
# ap = argparse.ArgumentParser()
# ap.add_argument("-s", "--save-model", type=int, default=-1,
# 	help="(optional) whether or not model should be saved to disk")
# ap.add_argument("-l", "--load-model", type=int, default=-1,
# 	help="(optional) whether or not pre-trained model should be loaded")
# ap.add_argument("-w", "--weights", type=str,
# 	help="(optional) path to weights file")
# args = vars(ap.parse_args())
#

def predict(fit_flag = False,save_flag = False,weight_file=None,testData=None):
    # if testData is None:
    #     (testData,testDataFiles) = image_to_np2.load_data_in_folder_to_predict()

    if fit_flag:
        (trainData, trainLabels) = image_to_np2.load_data()
        trainData = trainData.reshape((trainData.shape[0], image_to_np2.WIDTH, image_to_np2.HEIGHT, 1))
        trainData = trainData.astype("float32") / 255.0

        #show labels
        # import seaborn as sns
        # sns.countplot(trainLabels)
        # plt.title('Labels')
        # plt.savefig('figure/1.png')

        # transform the training and testing labels into vectors in the
        # range [0, classes] -- this generates a vector for each label,
        # where the index of the label is set to `1` and all other entries
        # to `0`; in the case of MNIST, there are 10 class labels
        trainLabels = to_categorical(trainLabels, 30)



        #split into train and test set
        X_train,X_val,y_train,y_val = train_test_split(trainData,trainLabels,test_size=0.20,random_state=2)
        print('shape of train data: ',X_train.shape)
        print('shape of validation data: ', X_val.shape)
        print('shape of train labels: ', y_train.shape)
        print('shape of validation label: ', y_val.shape)
        del trainData
        del trainLabels
        gc.collect()
        ntrain = len(X_train)
        nVal =len(X_val)



    if testData is not None:
        testData = testData.reshape((testData.shape[0], image_to_np2.WIDTH, image_to_np2.HEIGHT, 1))
        # scale data to the range of [0, 1]
        testData = testData.astype("float32") / 255.0

    def fit_model(opt,batch,ep):
        # initialize the optimizer and model
        print("[INFO] compiling model...")
        # opt = SGD(lr=0.1)
        # opt = optimizers.RMSprop(lr=0.0001)
        # opt = optimizers.Adadelta()
        model = LeNet.build(numChannels=1, imgRows=image_to_np2.WIDTH, imgCols=image_to_np2.HEIGHT,
                            numClasses=30,
                            weightsPath=weight_file if not fit_flag else None)

        model.compile(loss="categorical_crossentropy", optimizer=opt, metrics=["accuracy"])

        if fit_flag:
            try:
                name = opt.decay._shared_name
            except Exception as e:
                name = opt.beta_1._shared_name
            print("[INFO] training...{}_{}_{}".format(name.replace('/','_'),batch,ep))
            history = model.fit(X_train, y_train, batch_size=batch, epochs=ep, verbose=2, validation_data=(X_val, y_val))
            show_history(history, batch, ep, name.replace('/', '_'))
            print("[INFO] dumping weights to file...{}_{}_{}".format(name.replace('/','_'),batch,ep))
            if save_flag:
                model.save_weights('output/{}_{}_{}.hdf5'.format(name.replace('/','_'),batch,ep), overwrite=True)


    if fit_flag:
        # fit_model(optimizers.Adagrad(), 256, 20)
        # fit_model(optimizers.Adagrad(), 256, 30)
        # fit_model(optimizers.Adamax(), 256, 20)
        #fit_model(optimizers.Adamax(), 256, 30)
        # fit_model(optimizers.Adadelta(), 256, 20)
        fit_model(optimizers.Adadelta(), 256, 30)
        #fit_model(optimizers.Nadam(), 256, 20)
        fit_model(optimizers.Nadam(), 256, 30)
        #fit_model(optimizers.Nadam(), 512, 30)
        #fit_model(optimizers.Nadam(), 2048, 30)



        exit(0)


    #print("[INFO] evaluating...")
    model = LeNet.build(numChannels=1, imgRows=image_to_np2.WIDTH, imgCols=image_to_np2.HEIGHT,
                        numClasses=30,
                        weightsPath=weight_file if not fit_flag else None)

    model.compile(loss="categorical_crossentropy", optimizer=optimizers.Adagrad(), metrics=["accuracy"])

    #for test in testData:
    if testData is not None:
        predictions = []
        for i in range(0,len(testData)):
            probs = model.predict(testData[np.newaxis,i],batch_size=128, verbose=0)
            prediction = probs.argmax(axis=1)
            #print("[INFO] Predicted: {} {}".format(prediction[0],chr(prediction[0]+1488)))
            predictions.append(prediction[0])
            # if testData is None:
            #     image_to_np2.copy_image_to_folder(testDataFiles[i], prediction[0] + 1488)

    return predictions
    if args["save_model"] > 0:
    	print("[INFO] dumping weights to file...")
    	model.save_weights(args["weights"], overwrite=True)

def main():
    predict(True,True,'output/lenet_weights_10.hdf5')

if __name__ == "__main__":
    main()
