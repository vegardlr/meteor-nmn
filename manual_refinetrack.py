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

class DraggablePoints(object):
	def __init__(self, artists, tolerance=400):
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
		print "on_motion"
		if not self.currently_dragging:
			return
		if self.current_artist is None:
			return
		dx, dy = self.offset
		self.current_artist.center = event.xdata + dx, event.ydata + dy
		self.current_artist.figure.canvas.draw()


class Arrow(patches.Arrow):
	"""
	Custom marker
	"""
	def __init__(self,point,color):
		#name 'center' used to work with DraggablePOints
		self.center = point
		dx,dy = 100,100
		width = 40
		patches.Arrow.__init__(self,self.center[0]-dx,self.center[1]-dy,
			dx,dy,color=color,picker=True)
#                lines.Line2D.__init__(self,self.center[0],self.center[1],
#                        marker=u'*',linewidth=4,color=color)



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
		
		self.plot('m_landscape.jpg',(2480,952),(3552,608))

	def plot(self,filename,start_point,end_point):
		#Display image
		img = mpimg.imread(filename) 
		shape = numpy.shape(img)
		if shape[0] > shape[1]: img = img[::-1]
		imgplot = self.ax.imshow(img)
		
		#Cirlces
		circles = [patches.Circle(start_point, 50, fc='r', alpha=0.5),
				patches.Circle(end_point, 50, fc='b', alpha=0.5)]
		for patch in circles:
			self.ax.add_patch(patch)  
		self.dr = DraggablePoints(circles)

		#Arrows
#		arrows = [Arrow(start_point,'red'),Arrow(end_point,'yellow')] 
#		for patch in arrows:
#			self.ax.add_patch(patch)  
#		self.dr = DraggablePoints(arrows)


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

if __name__ == '__main__':
	app = wx.App()
	frame = MRTFrame()
	frame.Show()
	app.MainLoop()



