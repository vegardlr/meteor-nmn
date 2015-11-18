import matplotlib.pyplot as plt
import matplotlib.patches as patches
fig1 = plt.figure()
ax1 = fig1.add_subplot(111, aspect='equal')
w = 0.1
ax1.add_patch(patches.Rectangle((0.5-w/2, 0.5),0.5,w))
fig1.savefig('rect1.png', dpi=90, bbox_inches='tight')
