from django.shortcuts import render
from django.http import HttpResponse
from django.views import generic

#from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute

from datetime import datetime, timedelta

from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, UTCDateTimeAttribute

import json
import boto3

# Create your views here.

class IndexView(generic.TemplateView):
    template_name = "iot/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_data = Iot.queryChart(1)
        context['iot_data_temperature'] = all_data["iot_data_temperature"]
        context['iot_data_humidity'] = all_data["iot_data_humidity"]
        context['iot_data_pressure'] = all_data["iot_data_pressure"]
        context['iot_data_illumination'] = all_data["iot_data_illumination"]
        return context

def reload(request):
    data = request.POST.get("name-show-time-select")
    all_data = Iot.queryChart(int(data))
    return HttpResponse(json.dumps(all_data))

def switch(request):
    data = request.POST.get("type")
    now = datetime.now()
    iot = boto3.client('iot-data', region_name = 'ap-northeast-1')
    topic = 'pi/switch/op'
    payload = {
        "type": data,
        "timestamp": "{0:%Y-%m-%d %H:%M:%S}".format(now)
    }
    iot.publish(
        topic = topic,
        qos = 0,
        payload = json.dumps(payload, ensure_ascii=False)
    )

    return  HttpResponse('スイッチ操作({})が送信されました。({})'.format(data, now))

class Iot(Model):

    class Meta:
        table_name = "pi_info"
        region = 'ap-northeast-1'

    client_id = UnicodeAttribute(hash_key=True)
    timestamp = NumberAttribute(range_key=True)
    humidity = NumberAttribute()
    pressure = NumberAttribute()
    temperature = NumberAttribute()
    illumination = NumberAttribute()

    @staticmethod
    def queryChart(hours):
        now = datetime.now()
        time_1h = now - timedelta(hours = hours)
        time_1h_ts13 = int(time_1h.timestamp() * 1000)
        iot_data_temperature = []
        iot_data_humidity = []
        iot_data_pressure = []
        iot_data_illumination =[]
        for item in Iot.query('raspberrypi', Iot.timestamp > time_1h_ts13):
            x_time = datetime.fromtimestamp(
                item.timestamp / 1000).strftime("%Y/%m/%d %H:%M:%S")
            y_temperature = item.temperature
            y_humidity = item.humidity
            y_pressure = item.pressure
            y_illumination = item.illumination
            iot_data_temperature.append({"x": x_time, "y": y_temperature})
            iot_data_humidity.append({"x": x_time, "y": y_humidity})
            iot_data_pressure.append({"x": x_time, "y": y_pressure})
            iot_data_illumination.append({"x": x_time, "y": y_illumination})
        all_data = {
                "iot_data_temperature" : iot_data_temperature,
                "iot_data_humidity" : iot_data_humidity, 
                "iot_data_pressure" : iot_data_pressure,
                "iot_data_illumination" : iot_data_illumination
            }
        return all_data
