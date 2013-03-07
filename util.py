
import pandas as pd
from pandas.io.data import DataReader
import matplotlib.pyplot as plt
import numpy as np
from QuantLib import *
import urllib, urllib2,json, re, pylab,dateutil,datetime


class OptionCalculator(object):
    def __init__ (self,**kwargs):
        self.strike  = kwargs['strike']
        self.und     = kwargs['underlying']
        self.opttype = kwargs['opttype']
        self.vola    = kwargs['volatility']
        self.expiry  = kwargs['expiry']
        self.settle  = kwargs['settle']
        self.irate   = kwargs['irate']
        self.engine  = kwargs['engine']
        self.style   = kwargs['style']

        settlementDate=self.settle
        riskFreeRate = FlatForward(settlementDate, float(self.irate), Actual365Fixed())

        # option parameters
        #print self.style
        if self.style == 'american':
            exercise = AmericanExercise(settlementDate, self.expiry)
        else:
            exercise = EuropeanExercise(self.expiry)

        payoff = PlainVanillaPayoff(self.opttype, float(self.strike))

        # market data
        underlying = SimpleQuote(float(self.und))
        volatility = BlackConstantVol(settlementDate, TARGET(), float(self.vola), Actual365Fixed())
        dividendYield = FlatForward(settlementDate, 0.00, Actual365Fixed())

        self.process = BlackScholesMertonProcess(QuoteHandle(underlying),
                                            YieldTermStructureHandle(dividendYield),
                                            YieldTermStructureHandle(riskFreeRate),
                                            BlackVolTermStructureHandle(volatility))
        self.option = VanillaOption(payoff, exercise)


    def __setup (self):
        gridPoints = 800
        timeSteps = 801
        # method: binomial
        if self.engine in ('trigeorgis', 'lr','eqp','tian','jr','crr'):
            self.option.setPricingEngine(BinomialVanillaEngine(self.process,self.engine,timeSteps))
        #amer
        elif self.engine == 'Barone-Adesi-Whaley':
            self.option.setPricingEngine(BaroneAdesiWhaleyEngine(self.process))
        elif self.engine == 'Bjerksund-Stensland':
            self.option.setPricingEngine(BjerksundStenslandEngine(self.process))
        elif self.engine == 'finitediff':
            if self.style == 'american':
                self.option.setPricingEngine(FDAmericanEngine(self.process,timeSteps,gridPoints))
            else:
                self.option.setPricingEngine(FDEuropeanEngine(self.process,timeSteps,gridPoints))
        #
        elif self.engine=='analytic':
            self.option.setPricingEngine(AnalyticEuropeanEngine(self.process))
        elif self.engine=='integral':
            self.option.setPricingEngine(IntegralEngine(self.process))

    def calculate (self):
        self.__setup()
        try:
            npv=self.option.NPV()
        except:
            npv=None
        try:
            delta =self.option.delta()
        except:
            delta=None
        try:
            gamma=self.option.gamma()
        except:
            gamma=None
        try:
            vega=self.option.vega()
        except:
            vega=None
        try:
            theta=self.option.theta()
        except:
            theta=None
        return [npv,delta,gamma,vega,theta]

    def impliedvol(self,price):
        self.__setup()
        iv = None
        try:
            iv = self.option.impliedVolatility(price, self.process)
        except:
            pass
        return iv




class Ivol(object):
    def __init__ (self, ticker, exp, rate):
        self.ticker=ticker
        dt= exp #'121222'
        self.regex ='.*%s.*' % dt
        self.expiration = dateutil.parser.parse(dt)
        self.today = datetime.date.today()
        self.expiry = Date(self.expiration.day,self.expiration.month,self.expiration.year)
        self.settle = Date(self.today.day,self.today.month,self.today.year)
        self.irate = rate

    def getUnderlying (self):
        under_query = 'select BidRealtime, AskRealtime from yahoo.finance.quotes where symbol="%s"' %(self.ticker)
        wfcunder = Ivol.yqlfetch(under_query)
        self.midprice =( float(wfcunder['query']['results']['quote']['BidRealtime']) + float(wfcunder['query']['results']['quote']['AskRealtime']) ) /2.

    def getOptions (self):
        yql_query = 'select * from yahoo.finance.options where symbol="%s"' %(self.ticker)
        wfc = Ivol.yqlfetch(yql_query)
        op=wfc['query']['results']['optionsChain']['option']
        self.midputs=[ ((float(k['ask']) + float(k['bid']) )/2. , float(k['strikePrice']) ) for k in op if re.findall(self.regex,k['symbol']) and k['type']=='P'  ]
        self.midcalls=[ ((float(k['ask']) + float(k['bid']) )/2. , float(k['strikePrice']) ) for k in op if re.findall(self.regex,k['symbol']) and k['type']=='C'  ]

    @staticmethod
    def yqlurl (yql_query):
        url = 'http://query.yahooapis.com/v1/public/yql'
        env = 'store://datatables.org/alltableswithkeys'
        yql_query_url = 'http://query.yahooapis.com/v1/public/yql' + "?q=" + yql_query + "&format=json&env=" + env
        return yql_query_url

    @staticmethod
    def yqlfetch(qry):
        yql_query_url = Ivol.yqlurl(qry)
        resp = urllib.urlopen(yql_query_url).readlines()
        return json.loads(resp[0])

    def generate(self):
        cv=[]
        cs=[]
        pv=[]
        ps=[]
        for r in self.midcalls:
            if r[0]>0:
                c=OptionCalculator(strike=r[1],underlying=self.midprice, opttype=Option.Call,volatility=.15,irate=self.irate
                                        ,expiry=self.expiry
                                        ,settle= self.settle
                                        ,engine= 'finitediff'
                                        ,style='american' )
                vv=c.impliedvol(r[0])
                cv.append(vv)
                cs.append(r[1])

        for r in self.midputs:
            if r[0]>0:
                c=OptionCalculator(strike=r[1],underlying=self.midprice, opttype=Option.Put,volatility=.15,irate=.02
                                        ,expiry=self.expiry
                                        ,settle= self.settle
                                        ,engine= 'finitediff'
                                        ,style='american' )
                vv=c.impliedvol(r[0])
                pv.append(vv)
                ps.append(r[1])
        return ((cs,cv),(ps,pv))

    def plot(self,curve):
        pylab.figure(1)
        pylab.subplot(211)
        pylab.plot(curve[0][0],curve[0][1])
        pylab.grid(True)
        pylab.title("%s Call Implied Volatility, ref:%s exp:%s" %(self.ticker, self.midprice,self.expiry))

        pylab.subplot(212)
        pylab.plot(curve[1][0],curve[1][1])
        pylab.grid(True)
        pylab.title("%s Put Implied Volatility, ref:%s exp:%s" %(self.ticker, self.midprice,self.expiry))
        pylab.show()



def volcone(symbol):
    symbols = [symbol]

    data     = dict((sym, DataReader(sym, "yahoo")) for sym in symbols)
    panel    = pd.Panel(data).swapaxes('items', 'minor')
    close_px = panel['Close']
    #rets = close_px / close_px.shift(1) - 1
    rets = np.log(close_px / close_px.shift(1) )
    #annualize
    rets *= np.sqrt(252)
    std_30 = pd.rolling_std(rets, 30, min_periods=30)
    std_60 = pd.rolling_std(rets, 60, min_periods=60)
    std_90 = pd.rolling_std(rets, 90, min_periods=90)
    std_120 = pd.rolling_std(rets, 120, min_periods=120)

    a=std_30.describe()
    b=std_60.describe()
    c=std_90.describe()
    d=std_120.describe()

    for s in symbols:
        cone = pd.DataFrame(a[s],columns=['30'])
        cone.insert(1,'120',d[s])
        cone.insert(1,'90',c[s])
        cone.insert(1,'60',b[s])

        cone=cone.T

        del cone['count']
        del cone['std']

        cone.plot(title='%s Volatility Cone'%(s))
        plt.grid(True)
    plt.show()



import demjson,urllib2
def getOptionChain():
    url='http://www.google.com/finance/option_chain?q=AAPL&output=json'
    ii=urllib.urlopen(url).readline()
    ii = demjson.decode(ii)

