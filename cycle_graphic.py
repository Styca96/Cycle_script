import time
from multiprocessing.dummy import active_children
from tkinter import messagebox

import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
import matplotlib.transforms as mtrans
import pandas as pd

from libraries.Chamber import ACS_Discovery1200
from libraries.check_sequence import get_data
from libraries.Connection import Charger
from libraries.other_SCPI import CHROMA, HP6032A, ITECH, MSO58B

mplstyle.use("seaborn")
plt.rcParams["axes.grid.axis"] = "x"
# import pandas as pd


# ----- get data ----- #
df = get_data(all_data=True)
df.insert(0, "AbsTime", df.Time.cumsum())
df['Instrument'] = df['Instrument'].str.lower()
df_ch = df.loc[df['Instrument'] == "clim_chamber"]
df_arm = df.loc[df['Instrument'] == "armxl"]
df_ac = df.loc[df['Instrument'] == "ac_source"]
df_dc = df.loc[df['Instrument'] == "dc_source"]
TIME = df.AbsTime.min(), df.AbsTime.max()

# ----- plot ----- #
fig, (ax_ch, ax_arm, ax_ac, ax_dc) = plt.subplots(4, dpi=72)
fig.set_tight_layout(
    {"pad": 0.5, "w_pad": 0.1, "h_pad": 0.1, "rect": None}
    )
# fig.canvas.manager.full_screen_toggle()
# fig = plt.figure()
# gs = fig.add_gridspec(4, hspace=0)
# ax_arm, ax_arm, ax_ac, ax_dc = gs.subplots(sharex=True, sharey=False)


def parse(time_: list[int], data: list[int]):
    last_time = TIME[1]
    new_time = time_.copy()
    new_time.append(last_time)
    data.append(data[-1])
    return new_time, data


def set_spines(ax) -> None:
    """Configure spine for all twin axes"""

    def make_patch_spines_invisible(ax):
        ax.set_frame_on(True)
        ax.patch.set_visible(False)
        ax.spines[:].set_visible(False)

    ax.spines["right"].set_position(("axes", 1.05))
    make_patch_spines_invisible(ax)
    ax.spines["right"].set_visible(True)


# ----- chamber ----- #
# parse data
df_ch_temp = df_ch.loc[df_ch['Command'] == "write_setpoint"]
time_ = df_ch_temp.AbsTime.to_list()
args = df_ch_temp.Argument.to_list()
temp = []
hum = []
for i in args:
    sample = i.split()
    if sample[0] == "Temp":
        temp.append(int(sample[1]))
        hum.append(None)
    elif sample[0] == "Hum":
        hum.append(int(sample[1]))
        temp.append(None)
    else:
        hum.append(None)
        temp.append(None)
# plot 
cycle = iter(plt.rcParams['axes.prop_cycle'].by_key()['color'])
ax_ch.set_xlim(TIME)
# ax_ch.set_ylim(-50, 120) # fixed Temp limit
# ax_ch.set_xmargin(5)
ax_ch2 = ax_ch.twinx()
ax_ch.set_title("Climate Chamber")
ax_ch.set_ylabel("T")
ax_ch2.set_ylabel("H%")
# ax_ch.yaxis.set_label_coords(-0.1, 4/2)
p1, = ax_ch.step(*parse(time_, temp), where="post", label="T", color=next(cycle))
p2, = ax_ch2.step(*parse(time_, hum), where="post", label="H%", color=next(cycle))
lns = [p1, p2]
ax_ch.legend(handles=lns, loc='upper right')

# ----- armxl ----- #
# parse data
cycle = iter(plt.rcParams['axes.prop_cycle'].by_key()['color'])
df_arm_out = df_arm.loc[df_arm['Command'].str.endswith("charge_session.sh")]
time_out = df_arm_out.AbsTime.to_list()
output = df_arm_out.Command.str.startswith("start").to_list()
df_arm_set = pd.concat([df_arm, df_arm_out]).drop_duplicates(keep=False)
time_v = [0]
time_p = [0]
v_setpoint = [0]
p_setpoint = [0]
for abs_time, cmd, value in zip(df_arm_set.AbsTime,
                                df_arm_set.Command,
                                df_arm_set.Argument):
    values = value.split()
    if len(value.split()) == 2:
        time_v.append(abs_time)
        time_p.append(abs_time)
        v_setpoint.append(int(values[0])/10)
        p_setpoint.append(int(values[1])/10)
    elif cmd.endswith("power.sh"):
        time_p.append(abs_time)
        p_setpoint.append(int(values[0])/10)
    elif cmd.endswith("voltage.sh"):
        time_v.append(abs_time)
        v_setpoint.append(int(values[0])/10)

# plot 
ax_arm.set_xlim(TIME)
# ax_arm.set_xmargin(5)
ax_arm2 = ax_arm.twinx()
ax_arm3 = ax_arm.twinx()
ax_arm.set_title("ARMxl")
ax_arm.set_ylabel("V")
ax_arm2.set_ylabel("S")
ax_arm3.set_ylabel("State")
# ax_arm.yaxis.set_label_coords(-0.1, 4/2)
p1, = ax_arm.step(*parse(time_v, v_setpoint), where="post", label="V", color=next(cycle), alpha=.5)
# mtrans.offset_copy(ax_arm.transData, fig=fig, x=0.0, y=2*(0-1), units='points')
p2, = ax_arm2.step(*parse(time_p, p_setpoint), where="post", label="S", color=next(cycle), alpha=.5)
# mtrans.offset_copy(ax_arm.transData, fig=fig, x=0.0, y=2*(1-1), units='points')
p3, = ax_arm3.step(*parse(time_out, output), where="post", label="State", color=next(cycle), alpha=.5)
# mtrans.offset_copy(ax_arm3.transData, fig=fig, x=0.0, y=2*(2-1), units='points')
set_spines(ax_arm3)
lns = [p1, p2, p3]
ax_arm.legend(handles=lns, loc='upper right')
plt.show()
pass
