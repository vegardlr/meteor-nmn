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

	def connect(self):
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
		if DraggablePoint.lock is not self:
			return

		self.press = None
		DraggablePoint.lock = None

		# turn off the rect animation property and reset the background
		self.point.set_animated(False)
		self.background = None

		# redraw the full figure
		self.canvas.draw()

	def disconnect(self):
		'disconnect all the stored connection ids'
		self.canvas.mpl_disconnect(self.cidpress)
		self.canvas.mpl_disconnect(self.cidrelease)
		self.canvas.mpl_disconnect(self.cidmotion)





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

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
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
#		for patch in circles:
#			self.ax.add_patch(patch)  
#		self.dr = DraggablePoints(circles)

		self.drags = []
#		circles = [patches.Circle((0.32, 0.3), 0.03, fc='r', alpha=0.5),
#					   patches.Circle((0.3,0.3), 0.03, fc='g', alpha=0.5)]

		for circ in circles:
			self.ax.add_patch(circ)
			dr = DraggablePoint(circ)
			dr.connect()
			self.drags.append(dr)


class MRTControl(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1)
		font = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.BOLD)
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



