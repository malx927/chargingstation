# -*-coding:utf-8-*-

# import qrcode
# from PIL import Image
#
#
# def create_qrcode(content):
#     """创建二维码"""
#     qr = qrcode.QRCode(
#         version=1,
#         error_correction=qrcode.constants.ERROR_CORRECT_M,
#         box_size=12,
#         border=4,
#     )
#     qr.add_data(content)
#     qr.make(fit=True)
#     img = qr.make_image()
#     return img