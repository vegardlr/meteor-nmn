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

	def disconnect(self):
		'disconnect all the stored connection ids'
		self.canvas.mpl_disconnect(self.cidpress)
		self.canvas.mpl_disconnect(self.cidrelease)
		self.canvas.mpl_disconnect(self.cidmotion)


class DraggablePointControl(wx.Panel):
	def __init__(self, parent, point, label,color):
		wx.Panel.__init__(self, parent)

		self.label = wx.StaticText(self, label=label+":")
		self.xcoord = wx.TextCtrl(self)
		self.ycoord = wx.TextCtrl(self)
		self.button = wx.Button(self,label="Move point")
		self.button.Bind(wx.EVT_BUTTON,self.move_point)
		
		hbox = wx.BoxSizer(wx.HORIZONTAL)
		hbox.Add(self.label)
		hbox.Add(self.xcoord)
		hbox.Add(wx.StaticText(parent,label=" , "))
		hbox.Add(self.ycoord)
		hbox.Add(self.button)

		self.SetSizer(hbox)

		self.update(point)
		
	def update(self,xy):
		self.xcoord.SetValue("%f" % xy[0])
		self.ycoord.SetValue("%f" % xy[1])

	def move_point(self,event):
		print "Move",self.xcoord.GetValue(),self.ycoord.GetValue()


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

		self.SetAutoLayout(True)
		self.SetSizer(vbox)
		self.Layout()
	


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
		for pos,col in zip(event.positions, colors):
			circle = patches.Circle(pos, 50, fc=col, alpha=0.5)
			self.ax.add_patch(circle)  
			dr = DraggablePoint(circle)
			ctr = self.parent.controlpanel.new(pos,'Label',col)
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



