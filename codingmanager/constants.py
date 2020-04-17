# coding=utf-8
__author__ = 'Administrator'


# 电桩命令号
CMD_PILE_STATUS = b'\x01'
CMD_PILE_PARAMS = b'\x03'
CMD_PILE_CHARG_REPLY = b'\x04'
CMD_PILE_CAR_INFO = b'\x05'
CMD_PILE_CHARGING_STATUS = b'\x06'
CMD_PILE_STOP_CHARGING = b'\x07'
CMD_PILE_REQUEST_PRICE = b'\x08'
CMD_PILE_UPLOAD_BILL = b'\x09'
CMD_PILE_REQUEST_BALANCE = b'\x0a'
CMD_PILE_VERSION_INFO = b'\x81'
CMD_REQUEST_PILE_PARARMS = b'\x82'
CMD_CARD_CHARGING_REQUEST = b'\x83'
CMD_SEND_CHARGING = b'\x84'
CMD_REPLY_CHARGING = b'\x85'
CMD_SEND_STOP_CHARG = b'\x86'
CMD_FORCE_STOP_CHARG = b'\x87'
CMD_REPLY_PRICE = b'\x88'
CMD_REPLY_BILL = b'\x89'
CMD_RESPONSE_BALANCE = b'\x8a'
# 协议头尾字符
PROTOCAL_HEAD = b'\xAA\xAA'
PROTOCAL_TAIL = b'\x55\x55'

WORK_STATUS_FREE = 0
WORK_STATUS_CHARGING = 1
WORK_STATUS_ERROR = 2
WORK_STATUS_OVER_WITH_GUN = 3
WORK_STATUS_OFFLINE = 9
# 001直流单枪，010直流双枪，101交流单枪，110交流双枪，111功率主机； 011交直双枪,100功能分机 000非法桩

SEX_CHOICE = (
    (1, u'男'),
    (2, u'女'),
    (0, u'未知'),
)

USER_TYPE_CHOICE = (
    (0, u'临时用户'),
    (1, u'会员用户'),
    (2, u'超级用户'),
)

# 电站自有/运营公司/集团大客户
CHARGING_PRICE_TYPE = (
    (0, '运营公司价格'),
    (1, '电站自有价格'),
    (2, '集团客户价格'),
    (3, '离线充电价格'),
)

# 0 电桩模式(D4)
CHARGING_PILE_MODE = (
    (0, '整机输出模式'),
    (1, '主从分机模式'),
)

CHARGING_PILE_PROP = (
    (0, '未定义非法桩'),
    (1, '个人私有桩'),
    (2, '个人私有桩兼对外运营'),
    (3, '公司平台桩'),
    (4, '公司平台运营代理桩'),
    (5, '公司平台合作桩'),
    (6, '其他平台合作桩'),
    (7, '其他平台自营桩'),
)

CHARGING_PILE_POLICY = (
    (0, '系统默认策略'),
    (1, '定制充电策略'),
)

# 1 CC状态(D02-D00|D18-D16)
CC_STATUS = (
    (0, '不使用'),
    (1, '12V'),
    (2, '6V'),
    (3, '4V'),
    (4, '故障'),
)

# 2 CP状态(D05-D03|D21-D19)
CP_STATUS = (
    (0, '不使用'),
    (1, '12V'),
    (2, '9V'),
    (3, '6V'),
    (4, '故障'),
)

# 3 枪头温度(D07-D06|D23-D22)
GUN_TEMPERATURE = (
    (0, '不使用或正常'),
    (1, '第1路PT1000超温'),
    (2, '第2路PT1000超温'),
    (3, '两路超温或故障'),
)

# 4  电子锁状态(D09-D08|D25-D24)
ELEC_LOCK_STATUS = (
    (0, '正常'),
    (1, '上锁'),
    (2, '开锁'),
    (3, '故障'),
)

# 5 继电器状态(D11-D10|D27-D26)
RELAY_STATUS = (
    (0, '正常'),
    (1, '闭合'),
    (2, '粘连'),
    (3, '故障'),
)

# 6融断器状态(D13-D12|D29-D28)
FUSE_STATUS = (
    (0, '正常'),
    (1, '断开'),
    (2, '故障'),
)

# 7 电源模块状态(D47-D32|D63-D48)
POWER_MODULE_STATUS = (
    (0, '正常'),
    (1, '故障'),
)

# 8 柜内温度状态(D65-D64)
CABINET_TEMPERATURE_STATUS = (
    (0, '正常'),
    (1, '超温'),
)

# 9 防雷器或急停状态(D66|D67)
SPD_EMERGENCY_STATUS = (
    (0, '正常'),
    (1, '击穿'),
)

# 10 水浸状态(D68)
WATER_INPUT_STATUS = (
    (0, '正常'),
    (1, '水浸'),
)

# 11 开门状态(D69)
DOOR_STATUS = (
    (0, '正常'),
    (1, '开门'),
)

# 12 掉电状态(D70)
POWER_FAIL_STATUS = (
    (0, '正常'),
    (1, '掉电'),
)

# 13 掉电状态(D70)
ELEC_LEAK_STATUS = (
    (0, '正常'),
    (1, '漏电'),
)



# 14 枪运行状态编码(D7-D5)
GUN_WORKING_STATUS = (
    (0, '空闲'),
    (1, '充电中'),
    (2, '故障'),
    (3, '充电结束(未拔枪)'),
    (9, '离线'),
)

# 15 输出限小电流(D7-D4)
SMALL_CURRENT_STATUS = (
    (1, '启用'),
    (0, '不启用'),
)

# 17 充电国标协议编码
# 0 交流单相，1交流三相，2普天协议，3国标2011，4国标2015
INTER_PROTOCAL = (
    (0, '交流单相'),
    (1, '交流三相'),
    (2, '普天协议'),
    (3, '国标2011'),
    (4, '国标2015'),
)

# 18 用户充电方式编码(D13－D11)
USER_CHARGING_MODE = (
    (0, '充满为止'),
    (1, '按金额'),
    (2, '按分钟数'),
    (3, '按SOC'),
    (4, '按电量'),
)

# 19 电桩的充电模式编码
PILE_CHARGING_MODE = (
    (0, '后台'),
    (1, '本地离线'),
)

# 20 充电状态编码
PILE_CHARGING_STATUS = (
    (0, '成功'),
    (1, '枪未连接'),
    (2, '绝缘检测失败'),
    (3, '握手失败'),
    (4, '无法辨识的车辆或不支持的协议'),
)

# 21 运营属性编码(D7-D5)
BUSINESS_MODE = (
    (0, '私有'),
    (1, '自有公司运营'),
    (2, '自有平台运营'),
    (3, '其他公司运营'),
    (4, '运营商运营'),
)

DICOUNT_MODE = (
    (0.0, '不打折'),
    (9.5, '九五折'),
    (9.0, '九折'),
    (8.5, '八五折'),
    (8.0, '八折'),
    (7.5, '七五折'),
    (7.0, '七折'),
    (6.5, '六五折'),
    (6.0, '六折'),
    (5.5, '五五折'),
    (5.0, '五折'),
)

# 充电状态
GUN_CHARGING_STATUS = (
    (0, '充电枪未连接汽车，120S内无连接将主动停止充电'),
    (1, '充电枪已连接汽车，正在检测车辆信息'),
    (2, '正在充电'),
    (3, '已充满'),     # 对应 0
    (4, '后台中止'),    # 对应 1
    (5, '车端停止'),    # 对应 2
    (6, '故障停止'),    # 对应 3
)

# 充电订单状态

ORDER_STATUS = (
    (0, '空'),
    (1, '未结帐'),
    (2, '结账'),
)
# 订单状态
PAY_ORDER_STATUS = (
    (1, '已支付'),
    (0, '待支付'),
)

STATION_TYPES = (
    (1, "公共"),
    (50, "个人"),
    (100, "公交"),
    (101, "环卫"),
    (102, "物流"),
    (103, "出租车"),
    (255, "其他"),
)
STATION_STATUS = (
    (0, "未知"),
    (1, "建设中"),
    (5, "关闭下线"),
    (6, "维护中"),
    (50, "正常使用"),
)
STATION_PLACE = (
    (1, '居民区'),
    (2, '公共机构'),
    (3, '企事业单位'),
    (4, '写字楼'),
    (5, '工业园区'),
    (6, '交通枢纽'),
    (7, '大型文体设施'),
    (8, '城市绿地'),
    (9, '大型建筑配建停车场'),
    (10, '路边停车位'),
    (11, '城际高速服务区'),
    (255, '其他'),
)

NATIONAL_STANDARD = (
    (1, 2011),
    (2, 2015),
)

CONNECTOR_TYPE = (
    (1, '家用插座'),
    (2, '交流接口插座'),
    (3, '交流接口插头'),
    (4, '直流接口枪头'),
    (5, '无线充电座'),
    (6, '其他'),
)

GUN_NUM = (
    ('0', '0'),
    ('1', '1'),
)

STARTUP_MODEL = (
    (0, "微信启动"),
    (1, "储值卡启动"),
    (2, "E充网启动"),
    (3, "本地离线"),
)