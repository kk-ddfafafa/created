from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
import os
import datetime
import pytz
import pandas as pd
import numpy as np
import re
from statistics import mean, median,variance,stdev
import math


#ドライバの場所
path = "C:/Drivers/chromedriver_win32/chromedriver.exe"
DRIVER_PATH = os.path.join(os.path.dirname(path), "chromedriver")
#csvのpath
csv_path = 'C:/k-ba/keiba_nouryoku.csv'
csv_path2 = 'C:/k-ba/keiba_nouryoku_excel.csv'


def create_dayid(post):
    #日付IDを作成する。この後、そのIDがCSV内にあるか検索する。在れば、終了。無ければ、レースを検索する。
    if post:
        dayid = str(post)
    else:
        date = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))
        dayid = str(date.year) + str( date.month) + str(date.day)
    return dayid

def today_search(dayid):
    #レースを検索する。在れば、全レースをスクレイピングする。無ければ終了。
    urluma = 'https://www.keibalab.jp/db/race/' + str(dayid)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(DRIVER_PATH,options=options)
    driver.implicitly_wait(5)
    driver.get(urluma)
    html = driver.page_source.encode('utf-8')
    search = BeautifulSoup(html, "html.parser")
    if '見つかりませんでした' in search.prettify():
        driver.quit()
        print('見つかりません')
        return False
    #開催場を取得
    noresu = search.find_all('span')
    kaisaijou = []
    for p in noresu:
        if 'のレース傾向' in str(p):
            course = str(p)[70:72]
            kaisaijou.append(course)# kaisaijou = ['東京', '京都', '福島']
    jam = search.find_all('th', class_="bgGreenL white")
    jam = str(jam)
    ppp_p = []
    for jou in kaisaijou:
        if jou in jam:
            kaihime = jam.find(jou)
            kai = jam[kaihime - 2]
            kai = '0' + kai
            hime = jam[kaihime + 2]
            hime = '0' + hime
            posted_course = course_conv_rev(jou)
            ppp = posted_course + kai + hime# ppp=080506 開催場　回　日目
            ppp_p.append(ppp) #それぞれの開催場ごとのppp
    driver.quit()
    return ppp_p


def scr(post):
    dayid = create_dayid(post)
    ppp_or_false = today_search(dayid)
    if not ppp_or_false:
        print('False')
        return None
    df = pd.read_csv(csv_path)
    #  Dataframeのなかに同じdayidが含まれている場合はエスケープ
    if df['dayid'].astype(str).str.contains(dayid).sum() > 0:
        print('存在している')
        return None
    id_and_urls = {}# レースIDとそのURLを辞書形式で保存
    for ppp in ppp_or_false:
        for i in range(9,13):
            i = str(i)
            i = '09' if i == '9' else i
            year = dayid[:4]
            race_id = year + ppp + i
            url = 'https://racev3.netkeiba.com/race/shutuba_past.html?race_id=' + race_id
            race_id = str(dayid)+race_id[4:6]+race_id[-2:];print(race_id)
            id_and_urls[race_id] = url
    for url1 in id_and_urls.values():
        print(url1)
        all_data = [];ability_list = [];agari_list = [];ave3_list = [];pre_time = []#;print(url1)#pre_timeは予想タイム
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(DRIVER_PATH, options=options)
        driver.implicitly_wait(5)
        driver.get(url1)
        html = driver.page_source.encode('utf-8')
        soup = BeautifulSoup(html, "html.parser")
        if '障害オープン' in str(soup) or '障害３歳以上' in str(soup):
            continue
        # 出頭数と馬名 取得
        sdaf = soup.find_all('div', class_="Horse02")
        k_horse = []
        for i in sdaf:
            t = re.search(r'[ァ-ヶ].+?</a>', str(i))
            if t is None: continue
            k_horse.append(t.group()[:-4])
        if len(k_horse)==0:
            continue
        #本番距離取得
        honkyori = re.search(r'(ダ|芝)[0-9].+?m',str(soup.find_all('span'))).group()
        honsibada = honkyori[0]
        honbaba = course_conv(url1[-8:-6])
        # データ 取得
        table = soup.findAll("table")[0]
        rows = table.findAll("tr")
        for ii in range(1, len(k_horse) + 1):
            aaa = rows[ii].findAll('td')
            X = []
            Y = []#Yは指数化している。基準は100
            Z = []
            for i in range(5, 9):
                aaa_kaisai = str(aaa[i])
                if '休養' in aaa_kaisai or aaa_kaisai.find(
                        '>中</') > 0 or '障' in aaa_kaisai or 'class="Rest"' in aaa_kaisai:
                    continue
                if '0.0' in re.search(r'Data06.+?</div>', aaa_kaisai).group():  # 201903030409
                    continue
                if re.search(r'芝[0-9]', aaa_kaisai):
                    sibada = 0
                    ja = re.search(r'芝[0-9].+?[^0-9]', aaa_kaisai).group()
                elif re.search(r'ダ[0-9]', aaa_kaisai):
                    sibada = 1
                    ja = re.search(r'ダ[0-9].+?[^0-9]', aaa_kaisai).group()
                baba = re.search(r'span.+?\.[0-9]+\.[0-9].+?</s', aaa_kaisai).group()[-5:-3]  # babaは場所。阪神競馬場、東京競馬場など
                kyori = ja[1:5]
                data05 = re.search(r'Data05.+?</strong', aaa_kaisai).group()
                time = re.search(r'[0-9]:.+?<', data05).group()[:-2]
                joutai = re.search(r'Data05.+?[良|稍|重|不]', aaa_kaisai).group()[-1]
                kinryou = re.search(r'Data03.+?人.+?</div>', aaa_kaisai).group()[-11:-8]
                agari = re.search(r'Data06.+?\)', aaa_kaisai).group()[-5:-1]
                #yonkona = (re.search(r'Data06.+?</span', aaa_kaisai).group()[-8:-6])
                #if '-' in yonkona:
                #    yonkona = yonkona.replace('-', '')
                ave3_time = 60*int(time[0]) + float(time[2:])
                ave3 = (ave3_time-float(agari))/(int(kyori)-600)*600
                X.append(sisuuka(sibada, baba, kyori, time, joutai, kinryou));print(X)
                Y.append(agari_haron(baba,joutai,sibada, kyori, agari))
                Z.append(ave3)
            if len(X) > 3:
                ability = (sorted(X)[-1] + sorted(X)[-2] + sorted(X)[-3]) / 3  # 大きいもの三つピックアップ
            elif len(X) == 0:
                ability = 80
                Y.append(80)
                Z.append(45)
            else:
                ability = np.average(X)
            ability = round(ability, 2)
            # ability = round(sum(X)/len(X),2)
            agari_nouryoku = sum(Y) / len(Y)# 上がり３ハロン指数の平均
            t_agari_nouryoku = agari_nouryoku # t_に意味はないが差別化している.予想タイムの計算には不要なため
            t_agari_nouryoku = round(t_agari_nouryoku, 2)
            ave3 = round(sum(Z) / len(Z),2)
            ability_list.append(ability)
            agari_list.append(t_agari_nouryoku)
            ave3_list.append(ave3)
            # ave3リストからpre_timeリストを作る
            agari_nouryoku = agari_kijun(honsibada,honbaba,int(honkyori[1:5]),'良')/agari_nouryoku*100;print(agari_nouryoku)
            kkk = ave3*(int(honkyori[1:5])-600)/600 + agari_nouryoku
            pre_time.append(round(kkk,2))
        #能力とアガサンの偏差値作成
        v_time_nouryoku,v_agari,hensati_nouryoku,hensati_agari = hensati(ability_list,agari_list)
        hensati_nouryoku = np.round(hensati_nouryoku,2)
        hensati_agari = np.round(hensati_agari,2)
        #hensati_agariとhensati_nouryokuはnumpyのリスト。よってリストに変換するためにtolist()関数を使う
        hensati_nouryoku = hensati_nouryoku.tolist()
        hensati_agari = hensati_agari.tolist()
        #
        #これでリストが揃った。馬名->k_horse,能力->ability_list,アガサン->agari_list,ave3->ave3_list,偏差値リスト->hensati_list
        #all_dataに入れていく。このとき、18頭に満たない出頭数の場合はNoneで埋めていく
        if len(k_horse)<18:
            for i in range(1,(18-len(k_horse)+1)):
                k_horse.append(None)
                ability_list.append(None)
                agari_list.append(None)
                ave3_list.append(None)
                hensati_nouryoku.append(None)
                hensati_agari.append(None)
                pre_time.append(None)
        #all_dataぶちこみ。[dayid,race_id,馬名,能力,アガサン,ave3,能力の分散、アガサンの分散、偏差値能力、偏差値上がり]
        all_data.append(dayid)
        all_data += [p for p,v in id_and_urls.items() if v == url1]
        all_data += k_horse + ability_list + agari_list + ave3_list
        all_data.append(v_time_nouryoku);all_data.append(v_agari)
        all_data += hensati_nouryoku + hensati_agari + pre_time;print(all_data)
        all_data = pd.Series(all_data,index=df.columns)
        df = df.append(all_data,ignore_index=True)
    driver.close()
    driver.quit()
    df.to_csv(csv_path,index=False)
    df.to_csv(csv_path2, index=False,encoding='utf_8_sig')


#指数を作成する。馬場状態に関しては再考する余地あり
def sisuuka(sibada,baba,kyori,time,joutai,kinryou):
    kekka = 0
    kyori = int(kyori);time=int(time[0])*60+float(time[2:]);kinryou = float(kinryou)
    if kinryou > 56.0:
        time -= (kinryou -56)*0.1  # if 58kg and time=60 -> time = 60 - 0.2 = 59.8
    elif kinryou < 56.0:
        time += (56-kinryou) * 0.2 # if 54kg and time=60 -> time = 60 + 0.2 = 60.2
    if sibada == 0:
        #芝
        if joutai == '稍':
            time -= 0.5
        elif joutai == '重':
            time -= 0.8
        elif joutai == '不':
            time -= 1.5
    elif sibada == 1:
        #ダート
        if joutai == '稍':
            time += 0.2
        elif joutai == '重':
            time += 0.7
        elif joutai == '不':
            time += 0.8
    if sibada == 0:
        #芝
        if baba == '札幌' and kyori == 1000:
            record = 56.5
        elif baba == '札幌' and kyori == 1200:
            record = 67.5
        elif baba == '札幌' and kyori == 1500:
            record = 87.4
        elif baba == '札幌' and kyori == 1800:
            record = 105.7
        elif baba == '札幌' and kyori == 2000:
            record = 118.6
        elif baba == '札幌' and kyori == 2600:
            record = 158.7
        elif baba == '函館' and kyori == 1000:
            record = 57
        elif baba == '函館' and kyori == 1200:
            record = 66.8
        elif baba == '函館' and kyori == 1700:
            record = 101
        elif baba == '函館' and kyori == 1800:
            record = 105.7
        elif baba == '函館' and kyori == 2000:
            record = 117.8
        elif baba == '函館' and kyori == 2600:
            record = 157.3
        elif baba == '福島' and kyori == 1000:
            record = 56.7
        elif baba == '福島' and kyori == 1200:
            record = 67
        elif baba == '福島' and kyori == 1700:
            record = 100.4
        elif baba == '福島' and kyori == 1800:
            record = 105.3
        elif baba == '福島' and kyori == 2000:
            record = 117.3
        elif baba == '福島' and kyori == 2600:
            record = 157.3
        elif baba == '新潟' and kyori == 1000:
            record = 53.7
        elif baba == '新潟' and kyori == 1200:
            record = 67.5
        elif baba == '新潟' and kyori == 1400:
            record = 79
        elif baba == '新潟' and kyori == 1600:
            record = 91.5
        elif baba == '新潟' and kyori == 1800:
            record = 104.6
        elif baba == '新潟' and kyori == 2000:
            record = 116.4
        elif baba == '新潟' and kyori == 2200:
            record = 130.8
        elif baba == '新潟' and kyori == 2400:
            record = 144.6
        elif baba == '東京' and kyori == 1400:
            record = 79.4
        elif baba == '東京' and kyori == 1600:
            record = 90.5
        elif baba == '東京' and kyori == 1800:
            record = 104.2
        elif baba == '東京' and kyori == 2000:
            record = 116.1
        elif baba == '東京' and kyori == 2300:
            record = 138.5
        elif baba == '東京' and kyori == 2400:
            record = 140.6
        elif baba == '東京' and kyori == 2500:
            record = 148.2
        elif baba == '東京' and kyori == 3400:
            record = 209.4
        elif baba == '中山' and kyori == 1200:
            record = 66.7
        elif baba == '中山' and kyori == 1400:
            record = 83.2
        elif baba == '中山' and kyori == 1600:
            record = 90.3
        elif baba == '中山' and kyori == 1800:
            record = 104.9
        elif baba == '中山' and kyori == 2000:
            record = 117.8
        elif baba == '中山' and kyori == 2200:
            record = 130.1
        elif baba == '中山' and kyori == 2500:
            record = 149.5
        elif baba == '中山' and kyori == 2600:
            record = 160.3
        elif baba == '中山' and kyori == 3200:
            record = 199.3
        elif baba == '中山' and kyori == 3600:
            record = 221.6
        elif baba == '中京' and kyori == 1200:
            record = 66.7
        elif baba == '中京' and kyori == 1400:
            record = 79.6
        elif baba == '中京' and kyori == 1600:
            record = 92.3
        elif baba == '中京' and kyori == 2000:
            record = 118.3
        elif baba == '中京' and kyori == 2200:
            record = 129.9
        elif baba == '京都' and kyori == 1100:
            record = 67.5
        elif baba == '京都' and kyori == 1200:
            record = 66.7
        elif baba == '京都' and kyori == 1400:
            record = 79.0
        elif baba == '京都' and kyori == 1600:
            record = 91.3
        elif baba == '京都' and kyori == 1800:
            record = 103.9
        elif baba == '京都' and kyori == 2000:
            record = 116.8
        elif baba == '京都' and kyori == 2200:
            record = 129.7
        elif baba == '京都' and kyori == 2400:
            record = 142.6
        elif baba == '京都' and kyori == 3000:
            record = 181
        elif baba == '京都' and kyori == 3200:
            record = 192.5
        elif baba == '阪神' and kyori == 1200:
            record = 66.7
        elif baba == '阪神' and kyori == 1400:
            record = 79.3
        elif baba == '阪神' and kyori == 1600:
            record = 91.9
        elif baba == '阪神' and kyori == 1800:
            record = 104.4
        elif baba == '阪神' and kyori == 2000:
            record = 117.2
        elif baba == '阪神' and kyori == 2200:
            record = 130.1
        elif baba == '阪神' and kyori == 2400:
            record = 144.1
        elif baba == '阪神' and kyori == 2600:
            record = 157.1
        elif baba == '阪神' and kyori == 3000:
            record = 182.5
        elif baba == '小倉' and kyori == 1000:
            record = 56.6
        elif baba == '小倉' and kyori == 1200:
            record = 66.5
        elif baba == '小倉' and kyori == 1700:
            record = 99.5
        elif baba == '小倉' and kyori == 1800:
            record = 104.1
        elif baba == '小倉' and kyori == 2000:
            record = 116.9
        elif baba == '小倉' and kyori == 2600:
            record = 157.8
        elif kyori < 1600:
            print('か')
            record = 90.3 - (1600-kyori)*6/100
        elif 1600 <= kyori <= 2400:
            print('き')
            record = 90.3 + (kyori - 1600)*6/100
        elif 2400 < kyori :
            print('く')
            record = 90.3 + (kyori - 1600 + 100)*6/100
        else:
            print('け')
            record = time * 0.98
        kekka= round(record / time * 100,2)

    if sibada == 1:
        if baba == '札幌' and kyori == 1000:
            record = 57.5
        elif baba == '札幌' and kyori == 1700:
            record = 100.9
        elif baba == '札幌' and kyori == 2400:
            record = 152.1
        elif baba == '函館' and kyori == 1000:
            record = 57.7
        elif baba == '函館' and kyori == 1700:
            record = 101.7
        elif baba == '函館' and kyori == 2400:
            record = 152.8
        elif baba == '福島' and kyori == 1000:
            record = 58
        elif baba == '福島' and kyori == 1150:
            record = 66.9
        elif baba == '福島' and kyori == 1700:
            record = 103.1
        elif baba == '福島' and kyori == 2400:
            record = 150.2
        elif baba == '新潟' and kyori == 1200:
            record = 69.1
        elif baba == '新潟' and kyori == 1700:
            record = 106.6
        elif baba == '新潟' and kyori == 1800:
            record = 109.5
        elif baba == '新潟' and kyori == 2500:
            record = 158.8
        elif baba == '東京' and kyori == 1300:
            record = 76.1
        elif baba == '東京' and kyori == 1400:
            record = 81.5
        elif baba == '東京' and kyori == 1600:
            record = 93.8
        elif baba == '東京' and kyori == 2100:
            record = 126.7
        elif baba == '東京' and kyori == 2400:
            record = 148.6
        elif baba == '中山' and kyori == 1000:
            record = 58.4
        elif baba == '中山' and kyori == 1200:
            record = 68.7
        elif baba == '中山' and kyori == 1700:
            record = 103.1
        elif baba == '中山' and kyori == 1800:
            record = 108.5
        elif baba == '中山' and kyori == 2400:
            record = 148.8
        elif baba == '中山' and kyori == 2500:
            record = 158.6
        elif baba == '中京' and kyori == 1200:
            record = 69.7
        elif baba == '中京' and kyori == 1400:
            record = 80.3
        elif baba == '中京' and kyori == 1800:
            record = 107.6
        elif baba == '中京' and kyori == 1900:
            record = 115.9
        elif baba == '中京' and kyori == 2500:
            record = 164.6
        elif baba == '京都' and kyori == 1200:
            record = 69
        elif baba == '京都' and kyori == 1400:
            record = 81.7
        elif baba == '京都' and kyori == 1800:
            record = 107.8
        elif baba == '京都' and kyori == 1900:
            record = 113.7
        elif baba == '京都' and kyori == 2600:
            record = 163.3
        elif baba == '阪神' and kyori == 1200:
            record = 68.8
        elif baba == '阪神' and kyori == 1400:
            record = 81.5
        elif baba == '阪神' and kyori == 1800:
            record = 108.5
        elif baba == '阪神' and kyori == 2000:
            record = 121
        elif baba == '小倉' and kyori == 1000:
            record = 56.9
        elif baba == '小倉' and kyori == 1700:
            record = 101.8
        elif baba == '小倉' and kyori == 2400:
            record = 150.1
        elif kyori <1600:
            print('あ')
            record = 93.3-(1600-kyori)*6/100
        elif kyori >= 1600:
            print('い')
            record = 93.3 +(kyori-1600)*7/100
        else:
            record = time*0.95
        kekka = round( record / time * 100, 2)
    return kekka

def agari_kijun(sibada,baba,kyori,joutai):

    if sibada == '芝':
        sibada = 0
    elif sibada == 'ダ':
        sibada = 1
    if sibada == 0:
        #芝
        if baba == '札幌':
            if kyori == 1200:
                if joutai == '良':
                    kijun = 34.6
                elif joutai == '稍':
                    kijun = 35.5
                elif joutai == '重':
                    kijun = 35.8
                else:
                    kijun = 36.2
            elif kyori == 1500:
                if joutai == '良':
                    kijun = 34.6
                elif joutai == '稍':
                    kijun = 35.5
                elif joutai == '重':
                    kijun = 35.8
                else:
                    kijun = 36.2
            elif kyori == 1800:
                if joutai == '良':
                    kijun = 35.5
                elif joutai == '稍':
                    kijun = 35.9
                elif joutai == '重':
                    kijun = 36.5
                else:
                    kijun = 36.2
            elif kyori == 2000:
                if joutai == '良':
                    kijun = 35.5
                elif joutai == '稍':
                    kijun = 35.9
                elif joutai == '重':
                    kijun = 36.5
                else:
                    kijun = 36.2
            elif kyori == 2600:
                if joutai == '良':
                    kijun = 35.5
                elif joutai == '稍':
                    kijun = 35.9
                elif joutai == '重':
                    kijun = 36.5
                else:
                    kijun = 36.2
        elif baba == '函館':
            if kyori <= 1200:
                if joutai == '良':
                    kijun = 34.1
                elif joutai == '稍':
                    kijun = 35.0
                elif joutai == '重':
                    kijun = 35.6
                else:
                    kijun = 35.6
            elif kyori == 1800:
                if joutai == '良':
                    kijun = 34.8
                elif joutai == '稍':
                    kijun = 35.9
                elif joutai == '重':
                    kijun = 37.8
                else:
                    kijun = 35.5
            elif kyori == 2000:
                if joutai == '良':
                    kijun = 34.8
                elif joutai == '稍':
                    kijun = 35.9
                elif joutai == '重':
                    kijun = 37.8
                else:
                    kijun = 35.5
            elif kyori == 2600:
                if joutai == '良':
                    kijun = 4.8
                elif joutai == '稍':
                    kijun = 35.9
                elif joutai == '重':
                    kijun = 37.8
                else:
                    kijun = 35.5
        elif baba == '福島':
            if kyori == 1200:
                if joutai == '良':
                    kijun = 34.7
                elif joutai == '稍':
                    kijun = 34.9
                elif joutai == '重':
                    kijun = 35.5
                else:
                    kijun = 35.5
            elif kyori == 1700 or kyori == 1800:
                if joutai == '良':
                    kijun = 35.8
                elif joutai == '稍':
                    kijun = 36.3
                elif joutai == '重':
                    kijun = 36.6
                else:
                    kijun = 36.6
            elif kyori == 2000 or kyori == 2600:
                if joutai == '良':
                    kijun = 35.8
                elif joutai == '稍':
                    kijun = 36.3
                elif joutai == '重':
                    kijun = 36.6
                else:
                    kijun = 36.6
        elif baba == '新潟':
            if kyori == 1000:
                if joutai == '良':
                    kijun = 32.6
                elif joutai == '稍':
                    kijun = 33.1
                elif joutai == '重':
                    kijun = 33.2
                else:
                    kijun = 33.2
            elif kyori == 1200:
                if joutai == '良':
                    kijun = 34.0
                elif joutai == '稍':
                    kijun = 34.2
                elif joutai == '重':
                    kijun = 34.7
                else:
                    kijun = 34.4
            elif kyori == 1400:
                if joutai == '良':
                    kijun = 34.2
                elif joutai == '稍':
                    kijun = 34.2
                elif joutai == '重':
                    kijun = 34.7
                else:
                    kijun = 34.7
            elif kyori == 1600:
                if joutai == '良':
                    kijun = 33.5
                elif joutai == '稍':
                    kijun = 33.8
                elif joutai == '重':
                    kijun = 34.3
                else:
                    kijun = 34.6
            elif kyori == 1800 or kyori == 2000:
                if joutai == '良':
                    kijun = 33.5
                elif joutai == '稍':
                    kijun = 33.8
                elif joutai == '重':
                    kijun = 34.3
                else:
                    kijun = 34.6
            elif kyori == 2200 or kyori == 2400:
                if joutai == '良':
                    kijun = 34.7
                elif joutai == '稍':
                    kijun = 33.8
                elif joutai == '重':
                    kijun = 37.0
                else:
                    kijun = 37.0
        elif baba == '東京':
            if kyori == 1400:
                if joutai == '良':
                    kijun = 33.5
                elif joutai == '稍':
                    kijun = 33.9
                elif joutai == '重':
                    kijun = 34.4
                else:
                    kijun = 36.7
            elif kyori == 1600:
                if joutai == '良':
                    kijun = 33.9
                elif joutai == '稍':
                    kijun = 34.3
                elif joutai == '重':
                    kijun = 34.8
                else:
                    kijun = 36.7
            elif kyori >= 1800:
                if joutai == '良':
                    kijun = 34.1
                elif joutai == '稍':
                    kijun = 34.4
                elif joutai == '重':
                    kijun = 34.8
                else:
                    kijun = 36.7
        elif baba == '中山':
            if kyori == 1200:
                if joutai == '良':
                    kijun = 33.5
                elif joutai == '稍':
                    kijun = 34.5
                elif joutai == '重':
                    kijun = 35.9
                else:
                    kijun = 35.9
            elif kyori == 1600:
                if joutai == '良':
                    kijun = 34.3
                elif joutai == '稍':
                    kijun = 34.9
                elif joutai == '重':
                    kijun = 37.2
                else:
                    kijun = 37.2
            elif kyori == 1800 or kyori == 2000:
                if joutai == '良':
                    kijun = 34.4
                elif joutai == '稍':
                    kijun = 35.2
                elif joutai == '重':
                    kijun = 35.6
                else:
                    kijun = 36.2
            elif kyori == 2200:
                if joutai == '良':
                    kijun = 34.3
                elif joutai == '稍':
                    kijun = 34.9
                elif joutai == '重':
                    kijun = 37.2
                else:
                    kijun = 37.2
            elif kyori >= 2500:
                if joutai == '良':
                    kijun = 34.4
                elif joutai == '稍':
                    kijun = 35.2
                elif joutai == '重':
                    kijun = 35.6
                else:
                    kijun = 36.2
        elif baba == '中京':
            if kyori <= 1400:
                if joutai == '良':
                    kijun = 34.1
                elif joutai == '稍':
                    kijun = 34.8
                elif joutai == '重':
                    kijun = 35.5
                else:
                    kijun = 36.3
            elif kyori == 1600:
                if joutai == '良':
                    kijun = 34.6
                elif joutai == '稍':
                    kijun = 35.2
                elif joutai == '重':
                    kijun = 35.7
                else:
                    kijun = 37.5
            elif kyori > 1600:
                if joutai == '良':
                    kijun = 34.6
                elif joutai == '稍':
                    kijun = 35.2
                elif joutai == '重':
                    kijun = 35.7
                else:
                    kijun = 37.7
        elif baba == '京都':
            if kyori == 1200:
                if joutai == '良':
                    kijun = 33.8
                elif joutai == '稍':
                    kijun = 34.1
                elif joutai == '重':
                    kijun = 34.8
                else:
                    kijun = 36.0
            elif kyori == 1400:
                if joutai == '良':
                    kijun = 33.7
                elif joutai == '稍':
                    kijun = 34.1
                elif joutai == '重':
                    kijun = 34.8
                else:
                    kijun = 36.7
            elif kyori == 1600:
                if joutai == '良':
                    kijun = 34.0
                elif joutai == '稍':
                    kijun = 34.8
                elif joutai == '重':
                    kijun = 35.3
                else:
                    kijun = 37.4
            elif kyori == 1800:
                if joutai == '良':
                    kijun = 34.0
                elif joutai == '稍':
                    kijun = 34.9
                elif joutai == '重':
                    kijun = 35.5
                else:
                    kijun = 37.5
            elif kyori == 2000:
                if joutai == '良':
                    kijun = 34.4
                elif joutai == '稍':
                    kijun = 35.3
                elif joutai == '重':
                    kijun = 35.3
                else:
                    kijun = 37.5
            elif kyori == 2200:
                if joutai == '良':
                    kijun = 34.0
                elif joutai == '稍':
                    kijun = 34.9
                elif joutai == '重':
                    kijun = 35.5
                else:
                    kijun = 37.5
            elif kyori >= 2400:
                if joutai == '良':
                    kijun = 34.0
                elif joutai == '稍':
                    kijun = 34.9
                elif joutai == '重':
                    kijun = 35.5
                else:
                    kijun = 37.5
        elif baba == '阪神':
            if kyori <= 1400:
                if joutai == '良':
                    kijun = 34.1
                elif joutai == '稍':
                    kijun = 34.6
                elif joutai == '重':
                    kijun = 35.2
                else:
                    kijun = 36.4
            elif kyori == 1600 or kyori == 1800:
                if joutai == '良':
                    kijun = 34.1
                elif joutai == '稍':
                    kijun = 34.8
                elif joutai == '重':
                    kijun = 35.4
                else:
                    kijun = 36.5
            elif kyori == 2000 or kyori == 2200:
                if joutai == '良':
                    kijun = 34.6
                elif joutai == '稍':
                    kijun = 35.8
                elif joutai == '重':
                    kijun = 36.0
                else:
                    kijun = 37.5
            elif kyori == 2400 or kyori == 2600:
                if joutai == '良':
                    kijun = 34.1
                elif joutai == '稍':
                    kijun = 34.8
                elif joutai == '重':
                    kijun = 35.4
                else:
                    kijun = 36.5
            elif kyori == 3000:
                if joutai == '良':
                    kijun = 34.6
                elif joutai == '稍':
                    kijun = 35.8
                elif joutai == '重':
                    kijun = 36.0
                else:
                    kijun = 37.5
        elif baba == '小倉':
            if kyori == 1200:
                if joutai == '良':
                    kijun = 33.7
                elif joutai == '稍':
                    kijun = 34.2
                elif joutai == '重':
                    kijun = 34.7
                else:
                    kijun = 33.7
            elif kyori == 1700:
                if joutai == '良':
                    kijun = 34.8
                elif joutai == '稍':
                    kijun = 35.3
                elif joutai == '重':
                    kijun = 35.9
                else:
                    kijun = 33.7
            elif kyori >= 1800:
                if joutai == '良':
                    kijun = 34.8
                elif joutai == '稍':
                    kijun = 35.3
                elif joutai == '重':
                    kijun = 35.9
                else:
                    kijun = 34.8
        else:
            if kyori <= 1600:
                if joutai == '良':
                    kijun = 33.8
                elif joutai == '稍':
                    kijun = 34.3
                elif joutai == '重':
                    kijun = 34.8
                else:
                    kijun = 36.5
            elif kyori <= 2000:
                if joutai == '良':
                    kijun = 34.4
                elif joutai == '稍':
                    kijun = 35.3
                elif joutai == '重':
                    kijun = 35.3
                else:
                    kijun = 35.7
            if kyori > 2000:
                if joutai == '良':
                    kijun = 34.0
                elif joutai == '稍':
                    kijun = 35.0
                elif joutai == '重':
                    kijun = 35.5
                else:
                    kijun = 37.0
    else:
        if baba == '札幌':
            if kyori ==1000:
                if joutai == '良':
                    kijun = 35.3
                elif joutai == '稍':
                    kijun = 35.2
                elif joutai == '重':
                    kijun = 34.4
                else:
                    kijun = 34.2
            elif kyori >= 1700:
                if joutai == '良':
                    kijun = 37.2
                elif joutai == '稍':
                    kijun = 37.4
                elif joutai == '重':
                    kijun = 36.8
                else:
                    kijun = 37.1
        elif baba == '函館':
            if kyori == 1000:
                if joutai == '良':
                    kijun = 35.6
                elif joutai == '稍':
                    kijun = 35.4
                elif joutai == '重':
                    kijun = 35.0
                else:
                    kijun = 35.1
            elif kyori >= 1700:
                if joutai == '良':
                    kijun = 37.8
                elif joutai == '稍':
                    kijun = 37.6
                elif joutai == '重':
                    kijun = 36.9
                else:
                    kijun = 36.5
        elif baba == '福島':
            if kyori <= 1150:
                if joutai == '良':
                    kijun = 36.9
                elif joutai == '稍':
                    kijun = 36.6
                elif joutai == '重':
                    kijun = 36.2
                else:
                    kijun = 36.5
            elif kyori >= 1700:
                if joutai == '良':
                    kijun = 38.2
                elif joutai == '稍':
                    kijun = 38.0
                elif joutai == '重':
                    kijun = 37.7
                else:
                    kijun = 37.6
        elif baba == '新潟':
            if kyori == 1200:
                if joutai == '良':
                    kijun = 36.4
                elif joutai == '稍':
                    kijun = 36.7
                elif joutai == '重':
                    kijun = 36.2
                else:
                    kijun = 35.9
            elif kyori >= 1700:
                if joutai == '良':
                    kijun = 37.8
                elif joutai == '稍':
                    kijun = 38.0
                elif joutai == '重':
                    kijun = 38.0
                else:
                    kijun = 37.1
        elif baba == '東京':
            if kyori <= 1400:
                if joutai == '良':
                    kijun = 36.8
                elif joutai == '稍':
                    kijun = 36.0
                elif joutai == '重':
                    kijun = 35.5
                else:
                    kijun = 35.8
            elif kyori == 1600:
                if joutai == '良':
                    kijun = 36.9
                elif joutai == '稍':
                    kijun = 36.2
                elif joutai == '重':
                    kijun = 35.6
                else:
                    kijun = 36.0
            elif kyori >= 1700:
                if joutai == '良':
                    kijun = 36.9
                elif joutai == '稍':
                    kijun = 36.5
                elif joutai == '重':
                    kijun = 35.9
                else:
                    kijun = 36.2
        elif baba == '中山':
            if kyori <= 1200:
                if joutai == '良':
                    kijun = 35.7
                elif joutai == '稍':
                    kijun = 36.7
                elif joutai == '重':
                    kijun = 36.4
                else:
                    kijun = 36.1
            elif kyori >= 1700:
                if joutai == '良':
                    kijun = 37.7
                elif joutai == '稍':
                    kijun = 38.1
                elif joutai == '重':
                    kijun = 37.8
                else:
                    kijun = 37.5
        elif baba == '中京':
            if kyori <= 1400:
                if joutai == '良':
                    kijun = 36.7
                elif joutai == '稍':
                    kijun = 36.8
                elif joutai == '重':
                    kijun = 36.6
                else:
                    kijun = 36.4
            else:
                if joutai == '良':
                    kijun = 37.7
                elif joutai == '稍':
                    kijun = 37.8
                elif joutai == '重':
                    kijun = 37.5
                else:
                    kijun = 37.1
        elif baba == '京都':
            if kyori <= 1400:
                if joutai == '良':
                    kijun = 36.0
                elif joutai == '稍':
                    kijun = 36.0
                elif joutai == '重':
                    kijun = 35.8
                else:
                    kijun = 35.7
            else:
                if joutai == '良':
                    kijun = 37.7
                elif joutai == '稍':
                    kijun = 37.1
                elif joutai == '重':
                    kijun = 36.7
                else:
                    kijun = 36.7
        elif baba == '阪神':
            if kyori <= 1400:
                if joutai == '良':
                    kijun = 36.1
                elif joutai == '稍':
                    kijun = 36.2
                elif joutai == '重':
                    kijun = 35.8
                else:
                    kijun = 35.9
            else:
                if joutai == '良':
                    kijun = 37.9
                elif joutai == '稍':
                    kijun = 37.2
                elif joutai == '重':
                    kijun = 36.8
                else:
                    kijun = 36.8
        elif baba == '小倉':
            if kyori <= 1200:
                if joutai == '良':
                    kijun = 33.7
                elif joutai == '稍':
                    kijun = 34.2
                elif joutai == '重':
                    kijun = 34.7
                else:
                    kijun = 33.7
            elif kyori >= 1700:
                if joutai == '良':
                    kijun = 34.8
                elif joutai == '稍':
                    kijun = 35.3
                elif joutai == '重':
                    kijun = 35.9
                else:
                    kijun = 34.8
        else:
            if kyori <= 1400:
                if joutai == '良':
                    kijun = 36.0
                elif joutai == '稍':
                    kijun = 36.0
                elif joutai == '重':
                    kijun = 35.8
                else:
                    kijun = 36.2
            elif kyori >= 1400:
                if joutai == '良':
                    kijun = 37.7
                elif joutai == '稍':
                    kijun = 37.1
                elif joutai == '重':
                    kijun = 36.8
                else:
                    kijun = 37.8

    return kijun

def agari_haron(baba,joutai,sibada,kyori,agari):
    kyori = int(kyori) ; agari = float(agari)
    print(baba,kyori)
    kijun = agari_kijun(sibada,baba,kyori,joutai)
    agari = kijun/agari*100
    return agari

def hensati(nouryoku,agari_nouryoku):
    list_time_nouryoku = nouryoku
    list_agari = agari_nouryoku

    #それぞれの平均
    time_mean = np.average(list_time_nouryoku)
    agari_mean = np.average(list_agari)
    # それぞれの分散を求める
    v_time_nouryoku = np.round(variance(list_time_nouryoku),2)
    v_agari = np.round(variance(list_agari),2)
    # 標準偏差
    std_time_nouryoku = stdev(list_time_nouryoku)
    std_agari = stdev(list_agari)
    # 偏差値
    hensati_nouryoku = (((list_time_nouryoku-time_mean)*10)/std_time_nouryoku)+50
    hensati_agari = (((list_agari-agari_mean)*10)/std_agari)+50
    return v_time_nouryoku,v_agari,hensati_nouryoku,hensati_agari

def course_conv(posted_course):
    if posted_course == '01':course = '札幌'
    elif posted_course =='02':course = '函館'
    elif posted_course =='03':course = '福島'
    elif posted_course =='04':course = '新潟'
    elif posted_course =='05':course = '東京'
    elif posted_course =='06':course = '中山'
    elif posted_course =='07':course = '中京'
    elif posted_course =='08':course = '京都'
    elif posted_course =='09':course = '阪神'
    elif posted_course =='10':course = '小倉'
    return course

def course_conv_rev(posted_course):
    if posted_course == '札幌':course = '01'
    elif posted_course =='函館':course = '02'
    elif posted_course =='福島':course = '03'
    elif posted_course =='新潟':course = '04'
    elif posted_course =='東京':course = '05'
    elif posted_course =='中山':course = '06'
    elif posted_course =='中京':course = '07'
    elif posted_course =='京都':course = '08'
    elif posted_course =='阪神':course = '09'
    elif posted_course =='小倉':course = '10'
    return course


if __name__ == "__main__":
    nen = '2020'
    post =  nen + '0405'# Falseなら今日、20191110ならその日をスクレイピング
    if len(post) == 8:
        scr(post)
    else:
        print("error 8文字じゃない")


#git add .
#git commit -m "k"
#git push -u origin master

