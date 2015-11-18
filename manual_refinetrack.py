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
		'connect controls to marker (draggable point)'
		self.controls = controls
		self.controls.connect(self)
		'connect to all the events we need'
		self.cidpress = self.canvas.mpl_connect('button_press_event', 
				self.on_press)
		self.cidrelease = self.canvas.mpl_connect('button_release_event', 
				self.on_release)
		self.cidmotion = self.canvas.mpl_connect('motion_notify_event', 
				self.on_motion)

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

		hbox = wx.BoxSizer(wx.HORIZONTAL)
		hbox.Add(self.label,1,wx.LEFT|wx.CENTER)
		hbox.Add(self.xcoord)
		hbox.Add(wx.StaticText(parent,label=" , "))
		hbox.Add(self.ycoord)
		self.SetSizer(hbox)

		self.update(point)
		self.xcoord.Bind(wx.EVT_TEXT,self.move_marker)
		self.ycoord.Bind(wx.EVT_TEXT,self.move_marker)
		
	def connect(self,marker):
		self.marker = marker
	
	def update(self,xy):
		self.xcoord.SetValue("%.2f" % xy[0])
		self.ycoord.SetValue("%.2f" % xy[1])
	
	def getcoords(self):
		return [float(self.xcoord.GetValue()),float(self.ycoord.GetValue())]

	def move_marker(self,event):
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

		button_zoom = wx.Button(self,label="Close zoom")
		button_zoom.Bind(wx.EVT_BUTTON,self.close_zoom)
		vbox.Add(button_zoom)

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
	
	def snap_points(self,event):
		if not len(self.ylin) == len(self.controllers):
			print "Unequal length"
			return

		p0 = numpy.array([self.xlin[0],self.ylin[0]])
		p1 = numpy.array([self.xlin[-1],self.ylin[-1]])
		v1 = p1 - p0
		v1_unit = v1/numpy.linalg.norm(v1)

		for x,y,ctrl in zip(self.xlin,self.ylin,self.controllers):
			p = numpy.array([x,y])
			r = numpy.vdot(p-p0,v1_unit)
			p_nearest = r*v1_unit + p0
			print "Delta",p_nearest-p
			print "POints",p_nearest,p,p0
			if numpy.linalg.norm(p-p0) > 0:
				#self.parent.plotpanel.ax.plot([p[0],p_nearest[0]],[p[1],p_nearest[1]],'g')
				self.parent.plotpanel.ax.plot(p_nearest,'g',marker='x')
				self.parent.plotpanel.ax.plot(p,'g',marker='s')
				self.parent.plotpanel.canvas.draw()
				tja = input("Continue?")

			ctrl.update(p_nearest)
			ctrl.move_marker(None)

	def close_zoom(self,event):
		self.parent.plotpanel.close_zoom()


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
		self.canvas.mpl_connect('motion_notify_event', self.update_statusbar)
		self.toolbar = Toolbar(self.canvas) #matplotlib toolbar
		self.toolbar.Realize()

		self.line = []

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
		sizer.Add(self.toolbar, 0, wx.GROW)
		self.SetSizer(sizer)
		self.Fit()

	def update_statusbar(self,event):
		if event.xdata != None and event.ydata != None:
			self.parent.statusbar.SetStatusText(
					"Mouse coordinates:(%.2f, %.2f)" % 
					(event.xdata,event.ydata))
		
	def load(self,event):
		#Display image
		self.ax.imshow(event.img)
		self.close_zoom_x = event.xlim
		self.close_zoom_y = event.ylim
		self.ax.xaxis.tick_top()

		#Plot start/end points
		self.drags = []
		colors = self.color_range(event.frames)
		for pos, time, col in zip(event.positions, event.timestamps, colors):
			if pos != event.positions[0] and pos != event.positions[-1]:
				continue
			circle = patches.Circle(pos, 10, fc=col, alpha=0.2)
			self.ax.add_patch(circle)  
			dr = DraggablePoint(circle)
			time = datetime.utcfromtimestamp(time).strftime("t=%H:%M:%S.%f")
			ctr = self.parent.controlpanel.new(pos,str(time)[:-5],col)
			dr.connect(ctr)
			self.drags.append(dr)

		self.parent.controlpanel.show()

	def close_zoom(self):
		self.ax.set_xlim(self.close_zoom_x)
		self.ax.set_ylim(self.close_zoom_y) 
		self.canvas.draw()

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

		self.statusbar = wx.StatusBar(self)
		self.controlpanel = MRTControl(self)
		self.plotpanel = MRTPlot(self)
		self.SetStatusBar(self.statusbar)

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

		#Calculate xlim/ylim of meteor track in image
		x = [pos[0] for pos in self.positions]
		dx = (max(x)-min(x))/0.5
		y = [pos[1] for pos in self.positions]
		dy = (max(y)-min(y))/0.5
		self.xlim = [min(x)-dx,max(x)+dx]
		self.ylim = [min(y)-dy,max(y)+dy]


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



