
from PyQt4 import QtCore, QtGui
from magellangui import Ui_MainWindow
import sys
from util import *



class StartQT4(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.calcButton.clicked.connect(self.onCalculate)
        self.ui.PricercomboBox.activated.connect(self.onEngineChange)
        self.ui.volConeBtn.clicked.connect(self.onVolCone)
        self.ui.ivolBtn.clicked.connect(self.onImpliedVolCurve)

        self.lookup = { 'Trigeorgis' : 'trigeorgis'   #b
                        ,'LeisenReimer' : 'lr'        #b
                        ,'EQP'   : 'eqp'              #b
                        ,'Tian' : 'tian'              #b
                        ,'JarrowRudd' : 'jr'          #b
                        ,'CoxRossRubinstein'  : 'crr' #b
                        ,'Finite Difference' :'finitediff'
                        ,'Analytic'  : 'analytic'   #euro
                        ,'Integral': 'integral'    #euro
                        ,'Barone-Adesi-Whaley' : 'Barone-Adesi-Whaley'  #amer
                        ,'Bjerksund-Stensland' :'Bjerksund-Stensland'  #amer
                        }

    def onEngineChange (self):
        self.ui.AmericaradioButton.setCheckable(True)
        self.ui.EuroradioButton.setCheckable(True)
        engine= str(self.ui.PricercomboBox.currentText())
        if engine in ('Analytic','Integral'):
            self.ui.EuroradioButton.toggle()
            self.ui.AmericaradioButton.setCheckable(False)
        elif engine in ('Barone-Adesi-Whaley','Bjerksund-Stensland'):
            self.ui.AmericaradioButton.toggle()
            self.ui.EuroradioButton.setCheckable(False)

    def onCalculate(self):
        settledate = self.ui.settlemaneDate.date()
        expiry     = self.ui.dateEdit.date()
        k          = self.ui.StrikeLine.text()
        under      = self.ui.underlyingText.text()
        ivol       = self.ui.impvolLine.text()
        rate       = self.ui.rateLine.text()

        if self.ui.EuroradioButton.isChecked():
            style = 'euro'
        else:
            style = 'american'
        if self.ui.callRadio.isChecked():
            right = Option.Call
        else:
            right = Option.Put

        engine= str(self.ui.PricercomboBox.currentText())

        c=OptionCalculator(strike=k,underlying=under, opttype=right,volatility=ivol,irate=rate
                                ,expiry=Date(expiry.day(),expiry.month(),expiry.year())
                                ,settle=Date(settledate.day(),settledate.month(),settledate.year())
                                ,engine= self.lookup[engine],style=style )
        theos = c.calculate()
        self.ui.tableWidget.setRowCount(1)
        for i,g in enumerate(theos):
            self.ui.tableWidget.setItem(0,i,QtGui.QTableWidgetItem(str(g)) )

    def onVolCone(self):
        volcone(self.ui.coneTickerLine.text())

    def onImpliedVolCurve(self):
        ticker = self.ui.ivolTickerLine.text()
        expiry = self.ui.ivolExpiry.date()
        rate = self.ui.ivolratespin.text()
        strdate = "%s%s%s" %(expiry.year() % 100 , expiry.month(), expiry.day())
        i = Ivol(ticker,strdate,float(rate))
        i.getUnderlying()
        i.getOptions()
        c=i.generate()
        i.plot(c)



if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QtGui.QApplication(sys.argv)
    app.setStyle(QtGui.QStyleFactory.create('plastique'))

    myapp = StartQT4()
    myapp.show()
    sys.exit(app.exec_())


