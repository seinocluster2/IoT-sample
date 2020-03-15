#!python3 
# -*- coding: utf-8 -*-

import time
import os
import logging
import json
import yaml
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import boto3
import schedule
from bme280i2c import BME280I2C
from  tsl2572 import TSL2572
import lirc

logger = logging.getLogger("AWSIoTPythonSDK.core")
logger.setLevel(logging.INFO)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(name)s: %(levelname)s: %(message)s")
streamHandler.setFormatter(formatter)
#logger.addHandler(streamHandler)

# Custom callback
class CallbackContainer(object):

    def __init__(self, client, sns_arn, topic_report):
        self.__client = client
        self.__sns_arn = sns_arn
        self.__topic_report = topic_report
        self.__socket_path =  "/var/run/lirc/lircd"
        self.__remote = "lighting"
        self.__keys = ["push"]

    def messageSNS(self, client, userdata, message):
        sns = boto3.resource("sns")
        sns_message = json.loads(message.payload)
        logger.info("accept:{}".format(sns_message))
        if  sns_message["type"] == "light":
            with lirc.CommandConnection(socket_path = self.__socket_path) as conn:
                # The success rate increase when two run
                lirc.SendCommand(conn, remote = self.__remote, keys = self.__keys).run()
                lirc.SendCommand(conn, remote = self.__remote, keys = self.__keys).run()
        if  sns_message["type"] == "aircond":
            logger.info("aircond can't still be operated")
        response = sns.Topic(self.__sns_arn).publish(
            Message = json.dumps(sns_message),
            Subject = message.topic
        )

    def report(self):
        bme280ch1 = BME280I2C(0x76)
        if bme280ch1.meas() == False:
            return
        tsl2572 = TSL2572(0x39)
        if tsl2572.meas_single() == False:
            return
        req = {
                "state" :
                {
                    "reported" :
                    {
                        "pi_info" :
                        {
                            "temperature" : bme280ch1.T,
                            "pressure" : bme280ch1.P,
                            "humidity": bme280ch1.H,
                            "illumination" :  tsl2572.lux
                        }
                    }
                }
            }
        message = json.dumps(req)
        logger.info("reported:{}".format(message))
        self.__client.publish(self.__topic_report, message, 1)

def main():
    with open(os.path.join(os.path.dirname(__file__), "setting.yml")) as file:
         setting = yaml.safe_load(file)

    fileHandler = logging.FileHandler(filename = os.path.join(os.path.dirname(__file__), setting["LOG_FILE"]))
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)

    # Create, configure, and connect a shadow client.
    root_ca = os.path.join(os.path.dirname(__file__), setting["ROOT_CA"])
    private_key = os.path.join(os.path.dirname(__file__), setting["PRIVATE_KEY"])
    cert_file = os.path.join(os.path.dirname(__file__), setting["CERT_FILE"])

    myAWSIoTMQTTClient = AWSIoTMQTTClient(setting["SHADOW_CLIENT"])
    myAWSIoTMQTTClient.configureEndpoint(setting["HOST_NAME"], setting["PORT"])
    myAWSIoTMQTTClient.configureCredentials(root_ca, private_key, cert_file)

    myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
    myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
    myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
    myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

    topic_op =  setting["TOPIC_OP"]
    topic_report =  setting["TOPIC_REPORT"]

    myCallbackContainer = CallbackContainer(myAWSIoTMQTTClient, sns_arn = setting["SNS_ARN"], topic_report = topic_report)

    myAWSIoTMQTTClient.connect()

    # Perform synchronous subscribes
    myAWSIoTMQTTClient.subscribe(topic_op, 1, myCallbackContainer.messageSNS)

    for num in range(0, 60, 10):
        schedule.every().hour.at(":{:0>2}".format(num)).do(myCallbackContainer.report)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main()