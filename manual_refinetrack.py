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


class DraggablePoints(object):
	def __init__(self, artists, tolerance=40):
		for artist in artists:
			artist.set_picker(tolerance)
		self.artists = artists
		self.currently_dragging = False
		self.current_artist = None
		self.offset = (0, 0)

		for canvas in set(artist.figure.canvas for artist in self.artists):
			canvas.mpl_connect('button_press_event', 
				self.on_press)
			canvas.mpl_connect('button_release_event', 
				self.on_release)
			canvas.mpl_connect('pick_event', 
				self.on_pick)
			canvas.mpl_connect('motion_notify_event', 
				self.on_motion)

	def on_press(self, event):
		print "on_press"
		self.currently_dragging = True

	def on_release(self, event):
		print "on_release"
		self.currently_dragging = False
		self.current_artist = None

	def on_pick(self, event):
		print "on_pick"
		if self.current_artist is None:
			self.current_artist = event.artist
		x0, y0 = event.artist.center
		x1, y1 = event.mouseevent.xdata, event.mouseevent.ydata
		self.offset = (x0 - x1), (y0 - y1)

	def on_motion(self, event):
		if not self.currently_dragging: return
		if self.current_artist is None: return
		if event.xdata is None or event.ydata is None: return
		dx, dy = self.offset
		self.current_artist.x = event.xdata + dx
		self.current_artist.y = event.ydata + dy
		#self.current_artist.center = event.xdata + dx, event.ydata + dy
#		print "on_motion offset:%f,%f" % (self.offset)
#		print self.current_artist.center 
		self.current_artist.figure.canvas.draw()


class Arrow(patches.Arrow):
	"""
	Custom marker
	"""
	def __init__(self,point,color):
		#name 'center' used to work with DraggablePOints
		self.center = point
		dx,dy = 70,70
		width = 60
		patches.Arrow.__init__(self,self.center[0]-dx,self.center[1]-dy,
			dx,dy,width=width,color=color)
#				 lines.Line2D.__init__(self,self.center[0],self.center[1],
#						 marker=u'*',linewidth=4,color=color)



class MRTPlot(wx.Panel):
	"""
	Meteor Refine Track plot frame
	
	Displays image of meteor event with plotted on top markers for
	start- and end-points.
	"""
	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1)

		self.fig, self.ax = plt.subplots()

		self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
		self.toolbar = Toolbar(self.canvas) #matplotlib toolbar
		self.toolbar.Realize()

		# Now put all into a sizer
		sizer = wx.BoxSizer(wx.VERTICAL)
		# This way of adding to sizer allows resizing
		sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
		# Best to allow the toolbar to resize!
		sizer.Add(self.toolbar, 0, wx.GROW)
		self.SetSizer(sizer)
		self.Fit()
		
		#self.plot('m_landscape.jpg',(2480,952),(3552,608))

	def load(self,event):

		#Display image
		self.ax.imshow(event.img)

		#Plot start/end points
		circles = []
		colors = self.color_range(event.frames)
		for pos,col in zip(event.positions, colors):
			circle = patches.Circle(pos, 50, fc=col, alpha=0.5)
			circles.append(circle)
			self.ax.add_patch(circle)  
		self.drag = DraggablePoints(circles)

	def color_range(self,num_colors):
		colors=[]
		for i in numpy.arange(0., 360., 360. / num_colors):
			hue = i/360.
			lightness = (50 + numpy.random.rand() * 10)/100.
			saturation = (90 + numpy.random.rand()* 10)/100.
			colors.append(colorsys.hls_to_rgb(hue, lightness, saturation))
		return colors


class MRTControl(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1)
		font = wx.Font(18, wx.DEFAULT, wx.NORMAL, wx.BOLD)
		title = wx.StaticText(self,-1,label="CONTROLPANEL")
		title.SetFont(font)



class MRTFrame(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self,None,title="Manual Refine Track")
		self.plotpanel = MRTPlot(self)
		self.controlpanel = MRTControl(self)

		box = wx.BoxSizer(wx.HORIZONTAL)
		box.Add(self.plotpanel, 4, wx.LEFT|wx.TOP|wx.GROW)
		box.Add(self.controlpanel, 1, wx.LEFT|wx.TOP|wx.GROW)

		self.SetAutoLayout(True)
		self.SetSizer(box)
		self.Layout()

	def load(self,event):
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
	event = EventData("20151015","223929","harestua","cam3")
	frame.load(event)
	frame.Show()
	app.MainLoop()



