#!/usr/bin/env python
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
import matplotlib.ticker as mpltick
import numpy as np
# import matplotlib.transforms as mtrans
import pandas as pd

from libraries.Chamber import ACS_Discovery1200
from libraries.infer_data import get_data
from libraries.other_SCPI import ITECH


class MyLocator(mpltick.AutoMinorLocator):
    """AutoMinorLocator with 5 tick"""

    def __init__(self, n=5) -> None:
        super().__init__(n=n)


# mplstyle options
mplstyle.use("seaborn-darkgrid")
plt.rcParams["axes.grid.axis"] = "x"
plt.rcParams["xtick.minor.bottom"] = True
mpltick.AutoMinorLocator = MyLocator

##########################################################
# # -------------------- get data -------------------- # #
##########################################################
df: pd.DataFrame = get_data(all_data=True)
df.insert(0, "AbsTime", df.Time.cumsum())
line = pd.DataFrame({"AbsTime": 0, "Time": 0,  # create time 0 for starting
                     "Instrument": "-", "Command": "-",
                     "Argument": "-"}, index=[0])
df = pd.concat([line, df]).reset_index(drop=True)
TIME_SEC = [df.AbsTime.min(), df.AbsTime.max()]
df['Instrument'] = df['Instrument'].str.lower()  # case insensitive
df_ch = df.loc[df['Instrument'] == "clim_chamber"]
df_arm = df.loc[df['Instrument'] == "armxl"]
df_ac = df.loc[df['Instrument'] == "ac_source"]
df_dc = df.loc[df['Instrument'] == "dc_source"]


###################################################################
# # -------------------- plot and function -------------------- # #
###################################################################
def parse(time_: list[int], data: list[int]) -> tuple[list[int], list[int]]:
    """Parse data for mantain last data until last time\n
    Args:
        time_ (list[int]): time data
        data (list[int]): value data\n
    Returns:
        tuple[list[int], list[int]]: correct data
    """
    new_data = data.copy()
    new_data.append(data[-1])  # copy last value
    last_time = TIME_SEC[1]  # add last time
    new_time = time_.copy()
    new_time.append(last_time)
    hms_time = []
    for totsec in new_time:
        h = int(totsec//3600)
        m = int((totsec % 3600) // 60)
        sec = (totsec % 3600) % 60
        hms_time.append(f"{h:02d}:{m:02d}:{sec:04.1f}")
    mpl_date = mdates.datestr2num(hms_time)
    return mdates.num2date(mpl_date), new_data
    return new_time, new_data


def parse_vertical(time_: int):
    date_ , _ = parse([time_], [None])
    return mdates.date2num(date_[0])


def set_spines(ax) -> None:
    """Configure spine for all twin axes"""

    def make_patch_spines_invisible(ax):
        ax.set_frame_on(True)
        ax.patch.set_visible(False)
        ax.spines[:].set_visible(False)

    ax.spines["right"].set_position(("axes", 1.05))
    make_patch_spines_invisible(ax)
    ax.spines["right"].set_visible(True)


fig, (ax_ch, ax_arm, ax_ac, ax_dc) = plt.subplots(
    4, figsize=(8, 4), dpi=125, sharex=True
    )
fig.set_tight_layout(
    {"pad": 0.5, "w_pad": 0.1, "h_pad": 0.1, "rect": None}
    )
plt.minorticks_on()
ax_ch.grid(True, which='minor', axis='x', linestyle=':')
ax_arm.grid(True, which='minor', axis='x', linestyle=':')
ax_ac.grid(True, which='minor', axis='x', linestyle=':')
ax_dc.grid(True, which='minor', axis='x', linestyle=':')
ax_dc.tick_params(axis="x", which="both", colors="black")
date_form = mdates.DateFormatter("%H:%M:%S")
ax_dc.xaxis.set_major_formatter(date_form)

#########################################################
# # -------------------- chamber -------------------- # #
#########################################################
# parse data
df_ch_temp = df_ch.loc[df_ch['Command'] == "write_setpoint"]
time_ = [0] + df.AbsTime.iloc[df_ch_temp.index-1].to_list()
args = df_ch_temp.Argument.to_list()
temp = [None]  # add base value
hum = [None]  # add base value
for i in args:
    sample = i.split()
    if sample[0] == "Temp":
        val = temp
        not_val = hum
    elif sample[0] == "Hum":
        val = hum
        not_val = temp
    else:
        hum.append(None)
        temp.append(None)
        continue

    if len(sample) == 3:  # gradient setting
        index = len(val)
        start_time = time_[index]
        start_value = next(item for item in val[::-1] if item is not None)
        final_value = int(sample[1])
        step_setpoint = np.linspace(
            start_value, final_value, int(sample[2]) + 1
            )
        step_time = []
        for i in range(len(step_setpoint)-1):
            step_time.append(start_time + i*60)
            val.append(step_setpoint[i+1])
            not_val.append(not_val[-1])
        time_[index:index+1] = step_time  # insert new time
    else:
        val.append(int(sample[1]))
        not_val.append(not_val[-1])

# plot
cycle = iter(plt.rcParams['axes.prop_cycle'].by_key()['color'])
# ax_ch.set_ylim(-50, 120) # fixed Temp limit
# ax_ch.set_xmargin(5)
ax_ch2 = ax_ch.twinx()
ax_ch.set_ylabel("Chamber\n°C")
ax_ch2.set_ylabel("H%")
# ax_ch.yaxis.set_label_coords(-0.1, 4/2)
p1, = ax_ch.step(*parse(time_, temp), where="post", label="T",
                 color=next(cycle), alpha=.7)
p2, = ax_ch2.step(*parse(time_, hum), where="post", label="H%",
                  color=next(cycle), alpha=.7)
lns = [p1, p2]
leg = ax_ch2.legend(handles=lns, loc='upper right')
leg.set_draggable(True)

#######################################################
# # -------------------- armxl -------------------- # #
#######################################################
# parse data
cycle = iter(plt.rcParams['axes.prop_cycle'].by_key()['color'])
df_arm_out = df_arm.loc[df_arm['Command'].str.endswith("charge_session.sh")]
time_out = [0] + df.AbsTime.iloc[df_arm_out.index-1].to_list()
output = [None] + df_arm_out.Command.str.startswith("start").to_list()
df_arm_set = pd.concat([df_arm, df_arm_out]).drop_duplicates(keep=False)
# df_arm_set = df_arm.drop(df_arm_out.index)
time_v = [0]
time_p = [0]
time_r = [0]
v_setpoint = [None]  # add base value
p_setpoint = [None]  # add base value
r_setpoint = [None]  # add base value
for abs_time, cmd, value in zip(df_arm_set.AbsTime.index,
                                df_arm_set.Command,
                                df_arm_set.Argument):
    values = value.split()
    if len(value.split()) == 2:  # voltage & power
        time_v.append(df.AbsTime[abs_time-1])
        time_p.append(df.AbsTime[abs_time-1])
        v_setpoint.append(int(values[0])/10)
        p_setpoint.append(int(values[1])/10)
    elif cmd.endswith("power.sh"):
        time_p.append(df.AbsTime[abs_time-1])
        p_setpoint.append(int(values[0])/10)
    elif cmd.endswith("voltage.sh"):
        time_v.append(df.AbsTime[abs_time-1])
        v_setpoint.append(int(values[0])/10)
    elif cmd.endswith("reactive.sh"):
        time_r.append(df.AbsTime[abs_time-1])
        if int(values[0]) > 32000:
            r_setpoint.append((int(values[0])-32768)/-10)
        else:
            r_setpoint.append(int(values[0])/10)

# plot
# ax_arm.set_xmargin(5)
ax_arm2 = ax_arm.twinx()
ax_arm3 = ax_arm.twinx()
ax_arm.set_ylabel("ARMxl\nV")
ax_arm2.set_ylabel("kVA or kVAR")
ax_arm3.set_ylabel("State")
# ax_arm.yaxis.set_label_coords(-0.1, 4/2)
p1, = ax_arm.step(*parse(time_v, v_setpoint), where="post", label="V",
                  color=next(cycle), alpha=.7)
p2, = ax_arm2.step(*parse(time_p, p_setpoint), where="post", label="S",
                   color=next(cycle), alpha=.7)
p2b, = ax_arm2.step(*parse(time_r, r_setpoint), where="post", label="Q",
                    color=next(cycle), alpha=.7)
p3, = ax_arm3.step(*parse(time_out, output), where="post", label="State",
                   color=next(cycle), alpha=.7, linestyle="dashdot")
set_spines(ax_arm3)
lns = [p1, p2, p2b, p3]
leg = ax_arm3.legend(handles=lns, loc='upper right')
leg.set_draggable(True)

###########################################################
# # -------------------- AC source -------------------- # #
###########################################################
# parse data
cycle = iter(plt.rcParams['axes.prop_cycle'].by_key()['color'])
df_ac_out = df_ac.loc[df_ac['Command'].str.endswith("set_output")]
time_ = [0] + df.AbsTime.iloc[df_ac_out.index-1].to_list()
output = [None] + df_ac_out.Argument.isin(("on", "ON", "On", 1, True)).to_list()  # noqa: E501
df_ac_set = pd.concat([df_ac, df_ac_out]).drop_duplicates(keep=False)
time_v = [0]
time_f = [0]
v_setpoint = [None]  # add base value
f_setpoint = [None]  # add base value
for abs_time, cmd, value in zip(df_ac_set.AbsTime.index,
                                df_ac_set.Command,
                                df_ac_set.Argument):
    if cmd == "set_voltage":
        v_setpoint.append(int(value.split()[0]))
        time_v.append(df.AbsTime[abs_time-1])
    elif cmd == "set_frequency":
        f_setpoint.append(int(value.split()[0]))
        time_f.append(df.AbsTime[abs_time-1])
    elif cmd == "europe_grid":
        v_setpoint.append(230)
        time_v.append(df.AbsTime[abs_time-1])
        f_setpoint.append(50)
        time_f.append(df.AbsTime[abs_time-1])
    elif cmd == "usa_grid":
        v_setpoint.append(277)
        time_v.append(df.AbsTime[abs_time-1])
        f_setpoint.append(60)
        time_f.append(df.AbsTime[abs_time-1])

# plot
# ax_arm.set_xmargin(5)
ax_ac2 = ax_ac.twinx()
ax_ac3 = ax_ac.twinx()
ax_ac.set_ylabel("AC Source\nV")
ax_ac2.set_ylabel("Hz")
ax_ac3.set_ylabel("State")
# ax_ac.yaxis.set_label_coords(-0.1, 4/2)
p1, = ax_ac.step(*parse(time_v, v_setpoint), where="post", label="V",
                 color=next(cycle), alpha=.7)
p2, = ax_ac2.step(*parse(time_f, f_setpoint), where="post", label="Freq",
                  color=next(cycle), alpha=.7, linestyle="dashed")
p3, = ax_ac3.step(*parse(time_, output), where="post", label="State",
                  color=next(cycle), alpha=.7, linestyle="dashdot")
set_spines(ax_ac3)
lns = [p1, p2, p3]
leg = ax_ac3.legend(handles=lns, loc='upper right')
leg.set_draggable(True)

###########################################################
# # -------------------- DC source -------------------- # #
###########################################################
# parse data
cycle = iter(plt.rcParams['axes.prop_cycle'].by_key()['color'])
df_dc_out = df_dc.loc[df_dc['Command'].str.endswith("set_output")]
time_ = [0] + df.AbsTime.iloc[df_dc_out.index-1].to_list()
output = [None] + df_dc_out.Argument.isin(("on", "ON", "On", 1, True)).to_list()  # noqa: E501
df_dc_set = pd.concat([df_dc, df_dc_out]).drop_duplicates(keep=False)

time_vh = [0]
time_vl = [0]
time_ih = [0]
time_il = [0]
vh_setpoint = [None]  # add base value
vl_setpoint = [None]  # add base value
ih_setpoint = [None]  # add base value
il_setpoint = [None]  # add base value
mode = None
# plot messi prima per stampare i MODE in ax3 = state
# ax_arm.set_xmargin(5)
ax_dc2 = ax_dc.twinx()
ax_dc3 = ax_dc.twinx()
for abs_time, cmd, value in zip(df_dc_set.AbsTime.index,
                                df_dc_set.Command,
                                df_dc_set.Argument):
    if cmd == "set_function":
        # ax_dc.axvline(df.AbsTime[abs_time-1])
        ax_dc.axvline(parse_vertical(df.AbsTime[abs_time-1]))
        if value == "voltage":
            ax_dc3.text(parse_vertical(df.AbsTime[abs_time-1] + 0.1), 0.1,
                        "CV mode", rotation=90)
            if mode is not None:  # set to None all value becouse changed mode
                vh_setpoint.append(None)
                time_vh.append(df.AbsTime[abs_time-1])
                vl_setpoint.append(None)
                time_vl.append(df.AbsTime[abs_time-1])
                ih_setpoint.append(None)
                time_ih.append(df.AbsTime[abs_time-1])
            mode = "voltage"
        elif value == "current":
            ax_dc3.text(parse_vertical(df.AbsTime[abs_time-1] + 0.1), 0.1,
                        "CC mode", rotation=90)
            if mode is not None:  # set to None all value becouse changed mode
                vh_setpoint.append(None)
                time_vh.append(df.AbsTime[abs_time-1])
                ih_setpoint.append(None)
                time_ih.append(df.AbsTime[abs_time-1])
                il_setpoint.append(None)
                time_il.append(df.AbsTime[abs_time-1])
            mode = "current"
        continue

    split_val = value.split()
    if cmd == "set_voltage" or cmd == "set_current":
        if cmd == "set_voltage":
            val_time = time_vh
            val_list = vh_setpoint
        elif cmd == "set_current":
            val_time = time_ih
            val_list = ih_setpoint

        if len(split_val) == 2:
            start_time = val_time[-1]
            time_to_set = int(split_val[1])
            start_value = next(item for item in val_list[::-1]
                               if item is not None)
            final_value = int(split_val[0])
            step = (final_value - start_value) / (time_to_set / ITECH.TIMESTEP)
            values = np.arange(start_value, final_value, step
                               ).tolist() + [final_value]
            for i in range(len(values) - 1):
                val_time.append(df.AbsTime[abs_time-1] + i*ITECH.TIMESTEP)
                val_list.append(values[i+1])
        else:
            val_list.append(int(split_val[0]))
            val_time.append(df.AbsTime[abs_time-1])

    elif cmd == "set_v_limit":
        vh_setpoint.append(int(split_val[1]))
        time_vh.append(df.AbsTime[abs_time-1])
        vl_setpoint.append(int(split_val[0]))
        time_vl.append(df.AbsTime[abs_time-1])
    elif cmd == "set_c_limit":
        ih_setpoint.append(int(split_val[1]))
        time_ih.append(df.AbsTime[abs_time-1])
        il_setpoint.append(int(split_val[0]))
        time_il.append(df.AbsTime[abs_time-1])

# continue plot
ax_dc.set_ylabel("DC Source\nV")
ax_dc2.set_ylabel("A")
ax_dc3.set_ylabel("State")
# ax_dc.yaxis.set_label_coords(-0.1, 4/2)
p1, = ax_dc.step(*parse(time_vh, vh_setpoint), where="post", label="V/Vhigh",
                 color=next(cycle), alpha=.7)
p1b, = ax_dc.step(*parse(time_vl, vl_setpoint), where="post", label="Vlow",
                  color=next(cycle), alpha=.7, linestyle="dashed")
p2, = ax_dc2.step(*parse(time_ih, ih_setpoint), where="post", label="I/I+",
                  color=next(cycle), alpha=.7)
p2b, = ax_dc2.step(*parse(time_il, il_setpoint), where="post", label="I-",
                   color=next(cycle), alpha=.7, linestyle="dashed")
p3, = ax_dc3.step(*parse(time_, output), where="post", label="State",
                  color=next(cycle), alpha=.7, linestyle="dashdot")
set_spines(ax_dc3)
lns = [p1, p1b, p2, p2b, p3]
leg = ax_dc3.legend(handles=lns, loc="upper right")
leg.set_draggable(True)


# ----- show plot ----- #
plt.show()
pass
