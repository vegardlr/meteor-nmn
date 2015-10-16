import wx
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.image as mpimg
from matplotlib.backends.backend_wxagg import Toolbar, FigureCanvasWxAgg
import numpy

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
		self.currently_dragging = True

	def on_release(self, event):
		self.currently_dragging = False
		self.current_artist = None

	def on_pick(self, event):
		if self.current_artist is None:
			self.current_artist = event.artist
		x0, y0 = event.artist.center
		x1, y1 = event.mouseevent.xdata, event.mouseevent.ydata
		self.offset = (x0 - x1), (y0 - y1)

	def on_motion(self, event):
		if not self.currently_dragging:
			return
		if self.current_artist is None:
			return
		dx, dy = self.offset
		self.current_artist.center = event.xdata + dx, event.ydata + dy
		self.current_artist.figure.canvas.draw()


class Arrow(patches.Arrow):
	def __init__(self,point,color):
		dx,dy = 100,100
		width = 40
		self.center = point #name 'center' used to work with DraggablePOints
		patches.Arrow.__init__(self,self.center[0]-dx,
			self.center[1]-dy,dx,dy,
		width=width,color=color)



class MeteorPlot(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1)

		self.fig, self.ax = plt.subplots()	

		self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
		self.toolbar = Toolbar(self.canvas) #matplotlib toolbar
		self.toolbar.Realize()
		#self.toolbar.set_active([0,1])

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
		img = mpimg.imread('m_landscape.jpg') 
		imgplot = self.ax.imshow(img[::-1])
		
		#Add arrows
		arrows = [Arrow(start_point,'red'),Arrow(end_point,'yellow')] 
		for patch in arrows:
			self.ax.add_patch(patch)  
		dr = DraggablePoints(arrows)

		#Show everything
		#plt.show()


class MeteorControl(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1)
		wx.StaticText(self,-1,label="Hello")


class MeteorFrame(wx.Frame):
	def __init__(self,parent):
		wx.Frame.__init__(self,parent,title="Meteorframe")
				

if __name__ == '__main__':
	app = wx.App()
	frame = MeteorFrame(None)
	plotpanel = MeteorPlot(frame)
	controlpanel = MeteorControl(frame)
	frame.Show()
	app.MainLoop()
        	



