import cv2
import numpy as np
import ddddocr

#算法來源：https://github.com/hyzhangyong/platenumber/blob/master/platenumber.py

def preprocess(gray):
	# 直方圖均衡化
	# equ = cv2.equalizeHist(gray)
	# 高斯平滑
	gaussian = cv2.GaussianBlur(gray, (3, 3), 0, 0, cv2.BORDER_DEFAULT)
	# 中值濾波
	median = cv2.medianBlur(gaussian, 5)
	# Sobel算子，X方向求梯度
	sobel = cv2.Sobel(median, cv2.CV_8U, 1, 0, ksize = 3)
	# 二值化
	ret, binary = cv2.threshold(sobel, 170, 255, cv2.THRESH_BINARY)
	# 膨脹和腐蝕操作的核函數
	element1 = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 1))
	element2 = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 7))
	# 膨脹一次，讓輪廓突出
	dilation = cv2.dilate(binary, element2, iterations = 1)
	# 腐蝕一次，去掉細節
	erosion = cv2.erode(dilation, element1, iterations = 1)
	# 再次膨脹，讓輪廓明顯一些
	dilation2 = cv2.dilate(erosion, element2,iterations = 3)
	#cv2.imshow('dilation2',dilation2)
	#cv2.waitKey(0)
	return dilation2

def findPlateRegion(img):
    region=[]
    # 查找輪廓
    contours,hierarchy = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # 篩選面積小的
    for i in range(len(contours)):
        cnt = contours[i]
        # 計算該輪廓面積
        area = cv2.contourArea(cnt)
        # 面積小的篩選掉
        if area < 2000:
            continue
        
        # 輪廓近似，作用很小
        epsilon = 0.001 * cv2.arcLength(cnt,True)
        approx = cv2.approxPolyDP(cnt,epsilon,True)

        # 找到最小的矩形，該矩形可能有方向
        rect = cv2.minAreaRect(cnt)

        # box是矩形四個點的座標
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        # 計算高和寬
        height = abs(box[0][1] - box[2][1])
        width = abs(box[0][0] - box[2][0])

        # 車牌正常情況下長高比在2.7-5之間
        ratio = float(width) / float(height)

        if ratio > 5 or ratio < 2 :
            continue
        region.append(box)
    return region

#mode 0拍照模式 1模擬模式
def detect(mode,src):
    img = src if mode == 0 else cv2.imread(src)

    # 將圖片處理成最適大小
    h = img.shape[0]
    w = img.shape[1]
    offset = 1

    if w>=3000:
        offset = 0.65
    elif w>=2000:
        offset = 0.6
    elif w>=1000:
        offset = 0.7

    h = int(round(img.shape[0]*offset,0))
    w = int(round(img.shape[1]*offset,0))

    img = cv2.resize(img,(w,h),interpolation=cv2.INTER_CUBIC)

    # 轉為灰度圖
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    # 形態學變換的預處理
    dilation = preprocess(gray)

    # 車牌區域
    region = findPlateRegion(dilation)

    if len(region) > 0:
        box = region[0]

        ys = [box[0, 1], box[1, 1], box[2, 1], box[3, 1]]
        xs = [box[0, 0], box[1, 0], box[2, 0], box[3, 0]]
        ys_sorted_index = np.argsort(ys)
        xs_sorted_index = np.argsort(xs)

        x1 = box[xs_sorted_index[0], 0]
        x2 = box[xs_sorted_index[3], 0]
        
        y1 = box[ys_sorted_index[0], 1]
        y2 = box[ys_sorted_index[3], 1]

        img_plate = img.copy()
        img_plate = img_plate[y1:y2 , x1:x2]
        img_plate = cv2.cvtColor(img_plate,cv2.COLOR_RGB2GRAY)

        imgEncode = cv2.imencode('.jpg',img_plate)[1].tostring()

        ocr = ddddocr.DdddOcr()
        plate = ocr.classification(imgEncode).upper()
        plate = procText(plate)
        return plate
    else:
        return "No Plate"

def procText(text):
    eng = text[0:3]
    num = text[3:len(text)]
    if not eng.isalpha():
        eng = eng.replace('0','O').replace('1','I').replace('2','Z').replace('71','M').replace('1','L')
    if not num.isdigit():
        num = num.replace('O','0').replace('I','1').replace('Z','2').replace('M','71').replace('L','1')
    return eng + num

if __name__ == "__main__":
    detect('Pic/1.jpg')
