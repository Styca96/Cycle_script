#!/usr/bin/env python
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
# import matplotlib.transforms as mtrans
import pandas as pd

from libraries.check_sequence import get_data

mplstyle.use("seaborn-darkgrid")
plt.rcParams["axes.grid.axis"] = "x"

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
fig, (ax_ch, ax_arm, ax_ac, ax_dc) = plt.subplots(
    4, figsize=(8, 4), dpi=125, sharex=True
    )
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


# FIXME add initial 0 to data???
# ----- chamber ----- #
# parse data
df_ch_temp = df_ch.loc[df_ch['Command'] == "write_setpoint"]
time_ = [0] + df_ch_temp.AbsTime.to_list()
args = df_ch_temp.Argument.to_list()
temp = [None]
hum = [None]
for i in args:  # TODO write setpoint with time to set
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
# ax_ch.set_title("Chamber")
# ax_ch.set_title("Chamber", rotation='vertical',  y=0, x=-0.06)
# ax_ch.set_ylabel("T")
ax_ch.set_ylabel("Chamber\nT")
ax_ch2.set_ylabel("H%")
# ax_ch.yaxis.set_label_coords(-0.1, 4/2)
p1, = ax_ch.step(*parse(time_, temp), where="post", label="T",
                 color=next(cycle))
p2, = ax_ch2.step(*parse(time_, hum), where="post", label="H%",
                  color=next(cycle))
lns = [p1, p2]
leg = ax_ch2.legend(handles=lns, loc='upper right')
# leg = ax_dc3.legend(handles=lns, bbox_to_anchor=(1.1, 1), borderaxespad=0)
leg.set_draggable(True)

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
# ax_arm.set_title("ARMxl")
# ax_arm.set_title("ARMxl", rotation='vertical',  y=0, x=-0.06)
# ax_arm.set_ylabel("V")
ax_arm.set_ylabel("ARMxl\nV")
ax_arm2.set_ylabel("S")
ax_arm3.set_ylabel("State")
# ax_arm.yaxis.set_label_coords(-0.1, 4/2)
p1, = ax_arm.step(*parse(time_v, v_setpoint), where="post", label="V",
                  color=next(cycle), alpha=.5)
p2, = ax_arm2.step(*parse(time_p, p_setpoint), where="post", label="S",
                   color=next(cycle), alpha=.5)
p3, = ax_arm3.step(*parse(time_out, output), where="post", label="State",
                   color=next(cycle), alpha=.5, linestyle="dashdot")
set_spines(ax_arm3)
lns = [p1, p2, p3]
leg = ax_arm3.legend(handles=lns, loc='upper right')
# leg = ax_dc3.legend(handles=lns, bbox_to_anchor=(1.1, 1), borderaxespad=0)
leg.set_draggable(True)

# ----- AC source ----- #
# parse data
cycle = iter(plt.rcParams['axes.prop_cycle'].by_key()['color'])
df_ac_out = df_ac.loc[df_ac['Command'].str.endswith("set_output")]
time_ = df_ac_out.AbsTime.to_list()
output = df_ac_out.Argument.isin(("on", "ON", "On", 1, True)).to_list()
df_ac_set = pd.concat([df_ac, df_ac_out]).drop_duplicates(keep=False)
time_v = [0]
time_f = [0]
v_setpoint = [0]
f_setpoint = [0]
for abs_time, cmd, value in zip(df_ac_set.AbsTime,
                                df_ac_set.Command,
                                df_ac_set.Argument):
    if cmd == "set_voltage":
        v_setpoint.append(int(value.split()[0]))
        time_v.append(abs_time)
    elif cmd == "set_frequency":
        f_setpoint.append(int(value.split()[0]))
        time_f.append(abs_time)
    elif cmd == "europe_grid":
        v_setpoint.append(230)
        time_v.append(abs_time)
        f_setpoint.append(50)
        time_f.append(abs_time)
    elif cmd == "usa_grid":
        v_setpoint.append(277)
        time_v.append(abs_time)
        f_setpoint.append(60)
        time_f.append(abs_time)

# plot
ax_ac.set_xlim(TIME)
# ax_arm.set_xmargin(5)
ax_ac2 = ax_ac.twinx()
ax_ac3 = ax_ac.twinx()
# ax_ac.set_title("AC Source")
# ax_ac.set_title("AC Source", rotation='vertical',  y=0, x=-0.06)
# ax_ac.set_ylabel("V")
ax_ac.set_ylabel("AC Source\nV")
ax_ac2.set_ylabel("Hz")
ax_ac3.set_ylabel("State")
# ax_ac.yaxis.set_label_coords(-0.1, 4/2)
p1, = ax_ac.step(*parse(time_v, v_setpoint), where="post", label="V",
                 color=next(cycle), alpha=.5)
p2, = ax_ac2.step(*parse(time_f, f_setpoint), where="post", label="Freq",
                  color=next(cycle), alpha=.5)
p3, = ax_ac3.step(*parse(time_, output), where="post", label="State",
                  color=next(cycle), alpha=.5, linestyle="dashdot")
set_spines(ax_ac3)
lns = [p1, p2, p3]
leg = ax_ac3.legend(handles=lns, loc='upper right')
# leg = ax_dc3.legend(handles=lns, bbox_to_anchor=(1.1, 1), borderaxespad=0)
leg.set_draggable(True)

# ----- DC source ----- #
# parse data
cycle = iter(plt.rcParams['axes.prop_cycle'].by_key()['color'])
df_dc_out = df_dc.loc[df_dc['Command'].str.endswith("set_output")]
time_ = df_dc_out.AbsTime.to_list()
output = df_dc_out.Argument.isin(("on", "ON", "On", 1, True)).to_list()
df_dc_set = pd.concat([df_dc, df_dc_out]).drop_duplicates(keep=False)

time_vh = [0]
time_vl = [0]
time_ih = [0]
time_il = [0]
vh_setpoint = [None]
vl_setpoint = [None]
ih_setpoint = [None]
il_setpoint = [None]
mode = None
# plot messi prima per stampare i MODE in ax3 = state
ax_dc.set_xlim(TIME)
# ax_arm.set_xmargin(5)
ax_dc2 = ax_dc.twinx()
ax_dc3 = ax_dc.twinx()
for abs_time, cmd, value in zip(df_dc_set.AbsTime,  # TODO gestione time to set V e C # noqa: E501
                                df_dc_set.Command,
                                df_dc_set.Argument):
    if cmd == "set_function":
        ax_dc.axvline(abs_time)
        if value == "voltage":
            ax_dc3.text(abs_time + 0.1, 0.1, "CV mode", rotation=90)
            if mode is not None:
                vh_setpoint.append(None)
                time_vh.append(abs_time)
                vl_setpoint.append(None)
                time_vl.append(abs_time)
                ih_setpoint.append(None)
                time_ih.append(abs_time)
            mode = "voltage"
        elif value == "current":
            ax_dc3.text(abs_time + 0.1, 0.1, "CC mode", rotation=90)
            if mode is not None:
                vh_setpoint.append(None)
                time_vh.append(abs_time)
                ih_setpoint.append(None)
                time_ih.append(abs_time)
                il_setpoint.append(None)
                time_il.append(abs_time)
            mode = "current"

    if cmd == "set_voltage":
        vh_setpoint.append(int(value.split()[0]))
        time_vh.append(abs_time)
    elif cmd == "set_current":
        ih_setpoint.append(int(value.split()[0]))
        time_ih.append(abs_time)
    elif cmd == "set_v_limit":
        vh_setpoint.append(int(value.split()[1]))
        time_vh.append(abs_time)
        vl_setpoint.append(int(value.split()[0]))
        time_vl.append(abs_time)
    elif cmd == "set_c_limit":
        ih_setpoint.append(int(value.split()[1]))
        time_ih.append(abs_time)
        il_setpoint.append(int(value.split()[0]))
        time_il.append(abs_time)

# plot
# ax_dc.set_title("DC Source")
# ax_dc.set_title("DC Source", rotation='vertical',  y=0, x=-0.06)
# ax_dc.set_ylabel("V")
ax_dc.set_ylabel("DC Source\nV")
ax_dc2.set_ylabel("I")
ax_dc3.set_ylabel("State")
# ax_dc.yaxis.set_label_coords(-0.1, 4/2)
p1, = ax_dc.step(*parse(time_vh, vh_setpoint), where="post", label="V/Vhigh",
                 color=next(cycle), alpha=.5)
p1b, = ax_dc.step(*parse(time_vl, vl_setpoint), where="post", label="Vlow",
                  color=next(cycle), alpha=.5, linestyle="dashed")
p2, = ax_dc2.step(*parse(time_ih, ih_setpoint), where="post", label="I/I+",
                  color=next(cycle), alpha=.5)
p2b, = ax_dc2.step(*parse(time_il, il_setpoint), where="post", label="I-",
                   color=next(cycle), alpha=.5, linestyle="dashed")
p3, = ax_dc3.step(*parse(time_, output), where="post", label="State",
                  color=next(cycle), alpha=.5, linestyle="dashdot")
set_spines(ax_dc3)
lns = [p1, p1b, p2, p2b, p3]
leg = ax_dc3.legend(handles=lns, loc="upper right")
# leg = ax_dc3.legend(handles=lns, bbox_to_anchor=(1.1, 1), borderaxespad=0)
leg.set_draggable(True)

plt.show()
pass
