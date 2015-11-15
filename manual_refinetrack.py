"""
Manual Refine Track - MRT

"""

import wx
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.lines as lines
import matplotlib.image as mpimg
from matplotlib.backends.backend_wxagg import Toolbar, FigureCanvasWxAgg
import numpy
import urllib
import os, os.path
import errno
import colorsys
from datetime import datetime
#import distance


class DraggablePoint:
	"""
	Draggable Points as separate class and objects

	http://stackoverflow.com/questions/21654008/matplotlib-drag-overlapping-points-interactively
	"""
	lock = None #only one can be animated at a time
	def __init__(self, point):
		self.point = point
		self.canvas = self.point.figure.canvas
		self.axes = self.point.axes
		self.press = None
		self.background = None

	def connect(self, controls):
		'connect to all the events we need'
		self.cidpress = self.canvas.mpl_connect('button_press_event', 
				self.on_press)
		self.cidrelease = self.canvas.mpl_connect('button_release_event', 
				self.on_release)
		self.cidmotion = self.canvas.mpl_connect('motion_notify_event', 
				self.on_motion)
		self.controls = controls
		self.controls.connect(self)

	def on_press(self, event):
		if event.inaxes != self.point.axes: return
		if DraggablePoint.lock is not None: return
		contains, attrd = self.point.contains(event)
		if not contains: return
		self.press = (self.point.center), event.xdata, event.ydata
		DraggablePoint.lock = self

		# draw everything but the selected rectangle and store the pixel buffer
		self.point.set_animated(True)
		self.canvas.draw()
		self.background = self.canvas.copy_from_bbox(self.axes.bbox)

		# now redraw just the rectangle
		self.axes.draw_artist(self.point)

		# and blit just the redrawn area
		self.canvas.blit(self.axes.bbox)

	def on_motion(self, event):
		if DraggablePoint.lock is not self:
			return
		if event.inaxes != self.point.axes: return
		self.point.center, xpress, ypress = self.press
		dx = event.xdata - xpress
		dy = event.ydata - ypress
		self.point.center = (self.point.center[0]+dx, self.point.center[1]+dy)

		# restore the background region
		self.canvas.restore_region(self.background)

		# redraw just the current rectangle
		self.axes.draw_artist(self.point)

		# blit just the redrawn area
		self.canvas.blit(self.axes.bbox)

	def on_release(self, event):
		'on release we reset the press data'
		if DraggablePoint.lock is not self: return

		self.press = None
		DraggablePoint.lock = None

		# turn off the rect animation property and reset the background
		self.point.set_animated(False)
		self.background = None

		# redraw the full figure
		self.canvas.draw()

		# update widget controls
		self.controls.update([event.xdata,event.ydata])
	
	def move(self,pos):
		self.point.center = pos
		self.axes.draw_artist(self.point)
		self.canvas.blit(self.axes.bbox)
		self.canvas.draw()


	def disconnect(self):
		'disconnect all the stored connection ids'
		self.canvas.mpl_disconnect(self.cidpress)
		self.canvas.mpl_disconnect(self.cidrelease)
		self.canvas.mpl_disconnect(self.cidmotion)


class DraggablePointControl(wx.Panel):
	def __init__(self, parent, point, label,color):
		wx.Panel.__init__(self, parent,style=wx.SUNKEN_BORDER)

		self.label = wx.StaticText(self, label=label+":")
		self.xcoord = wx.TextCtrl(self)
		self.ycoord = wx.TextCtrl(self)
		self.button = wx.Button(self,label="Move point")
		self.button.Bind(wx.EVT_BUTTON,self.move_marker)
		
		hbox = wx.BoxSizer(wx.HORIZONTAL)
		hbox.Add(self.label,1,wx.LEFT|wx.CENTER)
		hbox.Add(self.xcoord)
		hbox.Add(wx.StaticText(parent,label=" , "))
		hbox.Add(self.ycoord)
		hbox.Add(self.button)

		self.SetSizer(hbox)

		self.update(point)
		
	def connect(self,marker):
		self.marker = marker
	
	def update(self,xy):
		self.xcoord.SetValue("%f" % xy[0])
		self.ycoord.SetValue("%f" % xy[1])
	
	def getcoords(self):
		return [float(self.xcoord.GetValue()),float(self.ycoord.GetValue())]

	def move_marker(self,event):
		print "Move",self.getcoords()
		self.marker.move(self.getcoords())


class MRTControl(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1)
		self.parent = parent
		self.controllers = []

	def new(self,point,label,color):
#		print "MRTControl: Add control box "
#		print point, label, color
		self.controllers.append(DraggablePointControl(self,point,label,color))
		return self.controllers[-1]

	def show(self):
		#print "MRTControl.show()",len(self.controllers)
		vbox = wx.BoxSizer(wx.VERTICAL)
		font = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD)
		title = wx.StaticText(self,-1,label="CONTROLPANEL")
		title.SetFont(font)
		vbox.Add(title)
		vbox.AddMany(self.controllers)
		#vbox.AddSpacer(self)

		self.lineparams = wx.StaticText(self,label="a=, b= ")
		vbox.Add(self.lineparams)
		button_linreg = wx.Button(self,label="Fit line")
		button_linreg.Bind(wx.EVT_BUTTON,self.linreg)
		vbox.Add(button_linreg)

		button_snap = wx.Button(self,label="Snap points")
		button_snap.Bind(wx.EVT_BUTTON,self.snap_points)
		vbox.Add(button_snap)

		self.SetAutoLayout(True)
		self.SetSizer(vbox)
		self.Layout()

	def linreg(self,event):
		x = []
		y = []
		for ctrl in self.controllers:
			xy = ctrl.getcoords()
			x.append(xy[0])
			y.append(xy[1])

		#Rewrite y=ax+b to y=Ap, where A = [x 1] and p=[[a],[b]]
		A = numpy.vstack([x, numpy.ones(len(x))]).T
		self.a,self.b = numpy.linalg.lstsq(A,y)[0]
		self.xlin = x
		self.ylin = numpy.array(x)*self.a + self.b
		self.lineparams.SetLabel("a=%f, b=%f " % (self.a,self.b))

		self.parent.plotpanel.plot_linreg(self.xlin,self.ylin)

	def get_angle(self, p0, p1=numpy.array([0,0]), p2=None):
		''' compute angle (in degrees) for p0p1p2 corner
		Inumpyuts:
			p0,p1,p2 - points in the form of [x,y]
		'''
		if p2 is None:
			p2 = p1 + numpy.array([1, 0])
		v0 = numpy.array(p0) - numpy.array(p1)
		v1 = numpy.array(p2) - numpy.array(p1)

		angle = numpy.math.atan2(numpy.linalg.det([v0,v1]),numpy.dot(v0,v1))
		return numpy.degrees(angle)
	
	def snap_points(self,event):
		if not len(self.ylin) == len(self.controllers):
			print "Unequal length"
			return

		for x,y,ctrl in zip(self.xlin,self.ylin,self.controllers):

			x0,y0 = self.xlin[0],self.ylin[0]
			x1,y1 = self.xlin[-1],self.ylin[-1]
			print self.get_angle([x,y],[x0,y0],[x1,y1])

#			start = [self.xlin[0],self.ylin[0]]
#			end = [self.xlin[-1],self.ylin[-1]]
#			print pnt2line(self.getcoords(),start,end)
			ctrl.update([x,y])
			ctrl.move_marker(None)

		


	


class MRTPlot(wx.Panel):
	"""
	Meteor Refine Track plot frame
	
	Displays image of meteor event with plotted on top markers for
	start- and end-points.
	"""
	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1)

		self.parent = parent

		self.fig, self.ax = plt.subplots()

		self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
		self.toolbar = Toolbar(self.canvas) #matplotlib toolbar
		self.toolbar.Realize()

		self.line = []

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
		sizer.Add(self.toolbar, 0, wx.GROW)
		self.SetSizer(sizer)
		self.Fit()
		
	def load(self,event):
		#Display image
		self.ax.imshow(event.img)

		#Plot start/end points
		self.drags = []
		colors = self.color_range(event.frames)
		for pos, time, col in zip(event.positions, event.timestamps, colors):
			circle = patches.Circle(pos, 10, fc=col, alpha=0.2)
			self.ax.add_patch(circle)  
			dr = DraggablePoint(circle)
			time = datetime.utcfromtimestamp(time).strftime("t=%H:%M:%S.%f")
			ctr = self.parent.controlpanel.new(pos,str(time),col)
			dr.connect(ctr)
			self.drags.append(dr)

		self.parent.controlpanel.show()

	def color_range(self,num_colors):
		colors=[]
		for i in numpy.arange(0., 360., 360. / num_colors):
			hue = i/360.
			lightness = (50 + numpy.random.rand() * 10)/100.
			saturation = (90 + numpy.random.rand()* 10)/100.
			colors.append(colorsys.hls_to_rgb(hue, lightness, saturation))
		return colors

	def plot_linreg(self,x,y):

		if len(self.line) > 0:
			self.line.pop(0).remove()
		self.line = self.ax.plot(x,y,'r')
		self.canvas.draw()





class MRTFrame(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self,None,title="Manual Refine Track",
				size=wx.Size(1200,800))
		self.controlpanel = MRTControl(self)
		self.plotpanel = MRTPlot(self)

		box = wx.BoxSizer(wx.HORIZONTAL)
		box.Add(self.plotpanel, 4, wx.LEFT|wx.TOP|wx.GROW)
		box.Add(self.controlpanel, 1, wx.LEFT|wx.TOP|wx.GROW)

		self.SetAutoLayout(True)
		self.SetSizer(box)
		self.Layout()

		#Test load event - add feature where events are selected
		event = EventData("20151015","223929","harestua","cam3")
		self.plotpanel.load(event)



class EventData:
	def __init__(self,date,time,station,camera):
		self.date = date
		self.time = time
		self.station = station
		self.camera = camera

		base = "http://norskmeteornettverk.no/meteor"
		cache = "./cache"
		self.create_path(cache)

		#Read image
		imgfile = station+"-"+date+time+"-gnomonic-labels.jpg"
		imgurl = base+"/"+date+"/"+time+"/"+station+"/"+camera+"/"+imgfile
		imgtmp = cache+"/"+date+time+station+camera+".jpg"
		if not os.path.isfile(imgtmp): urllib.urlretrieve(imgurl,imgtmp)
		self.img = mpimg.imread(imgtmp)
		shape = numpy.shape(self.img)
		#if shape[0] > shape[1]: self.img = self.img[::-1]

		#Read event data
		txturl = base+"/"+date+"/"+time+"/"+station+"/"+camera+"/event.txt"
		txttmp = cache+"/"+date+time+station+camera+".txt"
		if not os.path.isfile(txttmp): 
			urllib.urlretrieve(txturl,txttmp)
		fh = open(txttmp,'r')
		null = fh.readline()
		self.frames		 = int(fh.readline().split()[2])
		for i in range(0,8):
			null = fh.readline()
		self.positions	 = self.str2tuple(fh.readline().split()[2:])
		self.timestamps	 = self.str2float(fh.readline().split()[2:])
		self.coordinates = self.str2tuple(fh.readline().split()[2:])
		self.gnomonic	 = self.str2tuple(fh.readline().split()[2:])
		fh.close()

	def str2tuple(self,string_list):
		tuples = []
		for item in string_list:
			a,b = item.split(',')
			tuples.append((float(a),float(b)))
		return tuples

	def str2float(self,string_list):
		floats = []
		for item in string_list:
			floats.append(float(item))
		return floats

	def create_path(self,path):
		try:
			os.makedirs(path)
		except OSError as exception:
			if exception.errno != errno.EEXIST:
				raise








if __name__ == '__main__':
	app = wx.App()
	frame = MRTFrame()
	frame.Show()
	app.MainLoop()



