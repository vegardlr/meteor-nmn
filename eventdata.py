
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




