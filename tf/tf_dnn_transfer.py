import tensorflow as tf
import numpy as np
from datetime import datetime
from mnist import load_data_wrapper
import random

#train,valid,test = load_data_wrapper()

def numpy_to_tf(training_data):
    unzip = list(zip(*training_data))
    x = list(unzip[0])
    y = list(unzip[1])
    return x,y

def extract_from_n(tf_training_data,n):
    x,y = tf_training_data
    x = [t.ravel() for t,m in zip(x,y) if (sum(m[n:])!=0 if not isinstance(m,np.int64) else (m>=n))]
    f = lambda t : np.argmax(t) if not isinstance(t,np.int64) else t
    y = [f(t)-5 for t in y if (sum(t[n:])!=0  if not isinstance(t,np.int64) else (t>=n))]
    return x,y



n_inputs = 784
train_data = True
valid_data = False
n_outputs = 5
learning_rate = .5
n_epochs = 400
batch_size = 50

test_data = True
valid_data = False

now  = datetime.utcnow().strftime(("%Y%m%d%H%M%S"))
root_logdir = "tf_logs"
logdir = "{}/run-{}".format(root_logdir,now)

with tf.Session() as sess:

    #restore old model
    saver = tf.train.import_meta_graph('./mymode.ckpt.meta')
    saver.restore(sess,"./mymode.ckpt")

    graph = tf.get_default_graph()
    #obtain the last hidden layer

    hidden_5 = graph.get_tensor_by_name("dnn/Elu_4:0")

    #construct new output layer
    he_init = tf.contrib.layers.variance_scaling_initializer()
    logits = tf.layers.dense(hidden_5,kernel_initializer=he_init,units=n_outputs,name="trans_logits")
    #initialize new layer variables
    new_layer_init = tf.variables_initializer(graph.get_collection(tf.GraphKeys.GLOBAL_VARIABLES,scope="trans_logits"))
    sess.run(new_layer_init)

    train_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES,scope="trans_logits")

    #loss and training
    with tf.name_scope("transfer_loss"):
        y = graph.get_tensor_by_name("y:0")
        xentropy = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=y,logits=logits)
        loss = tf.reduce_mean(xentropy)
    with tf.name_scope("transfer_train"):
        optimizer = tf.train.AdamOptimizer(learning_rate)
        #account for batch norm updates: mean,gamma,beta
        extra_update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
        with tf.control_dependencies(extra_update_ops):
            training_op = optimizer.minimize(loss,var_list=train_vars)
        #https://stackoverflow.com/questions/41533489/how-to-initialize-only-optimizer-variables-in-tensorflow
        adam_initializers = [var.initializer for var in tf.global_variables() if 'transfer_train' in var.name or 'Adam' in var.name]
        sess.run(adam_initializers)
    y = graph.get_tensor_by_name("y:0")
    with tf.name_scope("trans_eval"):
        correct = tf.nn.in_top_k(logits,y,1)
        accuracy = tf.reduce_mean(tf.cast(correct,tf.float32))

    file_writer = tf.summary.FileWriter(logdir,tf.get_default_graph())


    #restore accuracy measure
    #accuracy= tf.get_default_graph().get_operation_by_name("eval/Mean")
    n=5
    train,valid,test = load_data_wrapper()
    #is_training = tf.placeholder(tf.bool,shape=(),name="is_training")
    valid = extract_from_n(numpy_to_tf(valid),n)
    test = extract_from_n(numpy_to_tf(test),n)

    #perform some conversion to make train list into X,y
    train = list(zip(*extract_from_n(numpy_to_tf(train),n)))



    num_train = len(train)

    file_writer = tf.summary.FileWriter(logdir,tf.get_default_graph())
    cost_log = tf.summary.scalar("Cost",loss)

    for epoch in range(n_epochs):

        #shuffle X,y together
        random.shuffle(train)
        X_train,y_train = zip(*train)


        mini_batchs = [
            (X_train[k:k+batch_size],y_train[k:k+batch_size]) for k in range(0,num_train,batch_size)
        ]
        num_batch = len(mini_batchs)
        for batch_index,batch in enumerate(mini_batchs):
            X_batch,y_batch = batch

            sess.run(training_op,feed_dict={"X:0":X_batch,"y:0":y_batch,"dnn/is_training:0":True})

            if batch_index%10 ==0:
                step = epoch*num_batch +batch_index
                cost_now = cost_log.eval(feed_dict={"X:0":X_batch,"y:0":y_batch,"dnn/is_training:0":False})
                file_writer.add_summary(cost_now,step)

        print("EPOCH: %d " %epoch,end="")
        if test_data:
            X_test,y_test =test
            accuracy_score = accuracy.eval(feed_dict={"X:0":X_test,"y:0":y_test,"dnn/is_training:0":False})
            print(", test: %f"  % accuracy_score,end="")
        if valid_data:
            X_valid,y_valid = valid
            accuracy_score = accuracy.eval(feed_dict={"X:0":X_valid,"y:0":y_valid,"dnn/is_training:0":False})
            print(", valid: %f" % accuracy_score,end="")
        print("\n")