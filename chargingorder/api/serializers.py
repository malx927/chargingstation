# -*-coding:utf-8-*-

import datetime
import os
from django.utils import timezone
from rest_framework.fields import SerializerMethodField
from rest_framework.permissions import AllowAny
from rest_framework.relations import HyperlinkedIdentityField
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from stationmanager.models import ChargingPile, ChargingGun

__author__ = 'malixin'


