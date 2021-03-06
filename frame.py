"""
Main frame
"""

import wx, wx.grid
import wx.lib.mixins.listctrl as listsortmixin
import pandas as pd
import numpy as np
import datetime
from wx import calendar
from money import Money
from collection import Collection, washer_names, dryer_names
from copy import deepcopy
import os
from load_mvl_main import load_mvl_main
from save_to_mvl_main import save_to_mvl_main
from sortedcontainers import SortedList

# dryer_names  = ['{}'.format(i) for i in range(1, 17)]
# dryer_names += ['{}'.format(i) for i in range(67, 71)]
# dryer_names += ['{}'.format(i) for i in range(72, 76)]
# dryer_names += ['20']
# dryer_names += ['{}'.format(i) for i in range(23, 28)]
#
# washer_names = ['A51',
#                 'B51',
#                 'S52',
#                 'A40',
#                 'W50',
#                 'E26',
#                 'F26',
#                 'D25',
#                 'C25',
#                 'B25',
#                 'A25',
#                 '*12',
#                 '*12',
#                 '*12',
#                 '*12',
#                 '*12',
#                 '*12',
#                 '*12',
#                 '*12',
#                 '*12',
#                 '*12',
#                 '*12',
#                 '*12',
#                 'E20',
#                 'D20',
#                 'C20',
#                 'B20',
#                 'A20'
#                 ]

# col1 = Collection('11/25/16', ['11/21/16', '11/25/16'],
#                   washer_names, dryer_names)
#
# col2 = Collection('11/18/16', ['11/14/16', '11/16/16', '11/18/16'],
#                   washer_names, dryer_names)
#
# with open('test_pickle.pkl', 'rb') as f:
#     col3 = cPickle.load(f)
#
today = datetime.datetime.now()
#
empty_col = Collection(today.strftime('%m/%d/%y'),
                       [(today - datetime.timedelta(days=4)).strftime('%m/%d/%y'),
                        today.strftime('%m/%d/%y')],
                       washer_names, dryer_names)


class ListPanel(wx.Panel, listsortmixin.ColumnSorterMixin):
    """
    Panel containing list of collection dates.
    """
    def __init__(self, parent):
        super(ListPanel, self).__init__(parent)

        self.frame = parent.GetTopLevelParent()

        self.col = None
        self.col_dict = None

        self.washer_period_dfs = None
        self.dryer_period_dfs = None

        self.df_meters = None
        self.df_changers = None
        self.df_others = None

        # panel sizer
        panel_sizer = wx.BoxSizer(wx.VERTICAL)

        # list control
        self.list_control = wx.ListCtrl(self, style=wx.LC_REPORT)

        # add columns to list
        self.list_control.InsertColumn(0, 'Week End')
        self.list_control.InsertColumn(1, 'Periods')

        # temp add for shape
        # cols = [col1, col2, col3]
        # cols = [empty_col]

        # add cols to list control, and make lookup dict, and index list
        self.col_dict = {}
        self.index_list = SortedList()
        # for ind, col in enumerate(sorted(cols)):
        #     we_string = col.week_end.strftime('%m/%d/%y')
        #     self.list_control.InsertStringItem(ind, we_string)
        #     self.list_control.SetStringItem(ind, 1, str(col.num_periods))
        #     self.list_control.SetItemData(ind, col.id)
        #     self.col_dict[col.id] = col

        panel_sizer.Add(self.list_control,
                        flag=wx.EXPAND,
                        proportion=1)

        self.SetSizer(panel_sizer)
        panel_sizer.Fit(self)

        # binder for double click on list item
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_double_click,
                  self.list_control)

    def split_col(self):
        """
        Splits collection dataframes up by periods.
        """
        washers = [pd.concat([self.col.df_washer[i],
                              self.col.df_washer['names']], axis=1)
                   for i in range(self.col.num_periods)]

        dryers = [pd.concat([self.col.df_dryer[i],
                             self.col.df_dryer['names']], axis=1)
                  for i in range(self.col.num_periods)]

        return washers, dryers

    def unsplit_col(self):
        """
        Unsplits collection dataframes back into single dfs.
        """
        per_period = ['weights', 'amounts']
        dfs = [self.washer_period_dfs, self.dryer_period_dfs]
        names = [self.col.washer_names, self.col.dryer_names]

        ret = []

        for i, df in enumerate(dfs):
            re_df = pd.DataFrame()

            for ind, period_df in enumerate(df):
                period_df = period_df[['weights', 'amounts']]
                cols = pd.MultiIndex.from_product([[ind], per_period],
                                                  names=['Period', None])
                period_df = pd.DataFrame(np.array(period_df), columns=cols)
                re_df = pd.concat([re_df, period_df], axis=1)

            re_df['names'] = names[i]

            ret.append(re_df)

        return ret

    def on_double_click(self, event=None, col_id=None):
        """
        Updates attributes, calls load.

        :param event:
        """
        if event is not None:
            selected = event.m_itemIndex
            col = self.col_dict[self.list_control.GetItemData(selected)]
        elif col_id is not None:
            try:
                col = self.col_dict[col_id]
            except KeyError:
                return
        else:
            raise('Not found')

        if col is not self.col:
            self.frame.save_collection()
            self.frame.load_collection(col)

    def save_collection(self, saves):
        # "save" currently selected
        if self.col is not None:
            self.col.df_washer, self.col.df_dryer = self.unsplit_col()
            self.col.df_meters, self.col.df_changers, self.col.df_others = saves

            self.col_dict[self.col.id] = self.col

    def load_collection(self, col):
        """
        Loads in new collection.
        :param col:
        """
        if col is not self.col:
            self.update(col)

    def update(self, col):
        """
        Updates proper attributes.

        :param col:
        """
        self.col = col
        self.frame.col = col

        self.washer_period_dfs, self.dryer_period_dfs = self.split_col()

        self.df_meters = col.df_meters
        self.df_changers = col.df_changers
        self.df_others = col.df_others

    def add_collection(self, col, load=True):
        """
        Adds a new collection.
        :param col:
        """
        if col.id not in self.col_dict:
            we_string = col.week_end.strftime('%m/%d/%y')

            self.index_list.add(col.week_end)
            ind = self.index_list.index(col.week_end)

            self.list_control.InsertStringItem(ind, we_string)
            self.list_control.SetStringItem(ind, 1, str(col.num_periods))
            self.list_control.SetItemData(ind, col.id)
            self.col_dict[col.id] = col

            # update calendar panel
            self.frame.calendar_panel.add_day(col.week_end)
            self.frame.calendar_panel.reset_cal()

            if load and col is not self.col:
                self.frame.save_collection()
                self.frame.load_collection(col)


class CalendarPanel(wx.Panel):
    """
    Panel containing simple calendar.
    """
    def __init__(self, parent):
        super(CalendarPanel, self).__init__(parent)

        self.frame = parent.GetTopLevelParent()

        # panel sizer
        panel_sizer = wx.BoxSizer(wx.VERTICAL)

        # calendar control
        self.calendar_control = calendar.GenericCalendarCtrl(parent=self,
            # style=calendar.CAL_SEQUENTIAL_MONTH_SELECTION
                                                             )

        panel_sizer.Add(self.calendar_control,
                        flag=wx.EXPAND | wx.TOP,
                        border=1)

        self.SetSizer(panel_sizer)
        panel_sizer.Fit(self)

        self.col_days = {}

        for col in self.frame.list_panel.col_dict.itervalues():
            date = col.week_end
            self.add_day(date)

        self.reset_cal()

        self.Bind(calendar.EVT_CALENDAR_MONTH,
                  self.reset_cal,
                  self.calendar_control)

        self.Bind(calendar.EVT_CALENDAR_YEAR,
                  self.reset_cal,
                  self.calendar_control)

        self.Bind(calendar.EVT_CALENDAR,
                  self.on_day_clicked,
                  self.calendar_control)

    def add_day(self, date):
        if date.year not in self.col_days:
            self.col_days[date.year] = {}

        if date.month not in self.col_days[date.year]:
            self.col_days[date.year][date.month] = []

        self.col_days[date.year][date.month].append(date.day)

    def reset_cal(self, event=None):
        # turn wx.datetime into datetime.date
        date = self.calendar_control.GetDate()
        ymd = map(int, date.FormatISODate().split('-'))
        date = datetime.date(*ymd)

        for day in range(1, 32):
            self.calendar_control.ResetAttr(day)

        if date.year in self.col_days:
            if date.month in self.col_days[date.year]:
                for day in self.col_days[date.year][date.month]:
                    self.calendar_control.SetAttr(day,
                        calendar.CalendarDateAttr(colBack=(255, 69, 0, 100)))

        if event is None:
            self.Refresh()

    def on_day_clicked(self, event):
        """
        """
        # turn wx.datetime into datetime.date
        date = self.calendar_control.GetDate()
        ymd = map(int, date.FormatISODate().split('-'))
        date = datetime.date(*ymd)

        col_id = hash(date.strftime('%m/%d/%y'))
        self.frame.list_panel.on_double_click(col_id=col_id)


class MeterPanel(wx.Panel):
    """
    Panel containing view of meter readings.
    """
    def __init__(self, parent):
        super(MeterPanel, self).__init__(parent)

        self.frame = parent.GetTopLevelParent()

        # panel sizer
        panel_sizer = wx.BoxSizer(wx.VERTICAL)

        # label
        title = wx.StaticText(self, label='Meter Readings')

        # create control
        self.grid = MyGrid(self, empty_col.df_meters, MyMetersDataSource)
        self.grid.SetColLabelSize(0)

        panel_sizer.Add(title,
                        border=5,
                        flag=wx.TOP | wx.BOTTOM | wx.LEFT)

        panel_sizer.Add(wx.StaticLine(self),
                        flag=wx.EXPAND)

        panel_sizer.Add(self.grid)

        self.SetSizer(panel_sizer)
        panel_sizer.Fit(self)

        self.Bind(wx.EVT_KEY_DOWN, self.on_enter)

    def on_enter(self, event):
        if event.GetKeyCode() == wx.WXK_RETURN or event.GetKeyCode() == \
                wx.WXK_NUMPAD_ENTER:

                if self.grid.GetGridCursorRow() == 5:
                    self.GetParent().move_to_next(0)

        event.Skip()

    def update_grid(self, values):
        for i, value in enumerate(values):
            self.grid.Table.SetValue(i, 0, value)

        msg = wx.grid.GridTableMessage(self.grid.Table,
                                       wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.grid.ProcessTableMessage(msg)


class ChangerPanel(wx.Panel):
    """
    Panel containing view of meter readings.
    """
    def __init__(self, parent):
        super(ChangerPanel, self).__init__(parent)

        self.frame = parent.GetTopLevelParent()

        # panel sizer
        panel_sizer = wx.BoxSizer(wx.VERTICAL)

        # label
        title = wx.StaticText(self, label='Changer Readings')

        # create control
        self.grid = MyGrid(self, empty_col.df_changers, MyChangersDataSource)
        self.grid.SetColLabelSize(0)

        panel_sizer.Add(title,
                        border=5,
                        flag=wx.TOP | wx.BOTTOM | wx.LEFT)

        panel_sizer.Add(wx.StaticLine(self),
                        flag=wx.EXPAND)

        panel_sizer.Add(self.grid)

        self.SetSizer(panel_sizer)
        panel_sizer.Fit(self)

        self.Bind(wx.EVT_KEY_DOWN, self.on_enter)

    def on_enter(self, event):
        if event.GetKeyCode() == wx.WXK_RETURN or event.GetKeyCode() == \
                wx.WXK_NUMPAD_ENTER:

                if self.grid.GetGridCursorRow() == 6:
                    if self.grid.GetGridCursorCol() == 1:
                        self.GetParent().move_to_next(1)
                    else:
                        self.grid.GoToCell(0, 1)
                        return
        event.Skip()

    def update_grid(self, values):
        left = values['left']
        right = values['right']

        for i, column in enumerate([left, right]):
            for j, value in enumerate(column):
                # print i, j, value
                self.grid.Table.SetValue(j, i, value)

        msg = wx.grid.GridTableMessage(self.grid.Table,
                                       wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.grid.ProcessTableMessage(msg)


class OtherPanel(wx.Panel):
    """
    Panel containing view of meter readings.
    """
    def __init__(self, parent):
        super(OtherPanel, self).__init__(parent)

        self.frame = parent.GetTopLevelParent()

        # panel sizer
        panel_sizer = wx.BoxSizer(wx.VERTICAL)

        # label
        title = wx.StaticText(self, label='Other Coin Amounts')

        # create control
        self.grid = MyGrid(self, empty_col.df_others, MyOthersDataSource)
        self.grid.SetColLabelSize(0)

        panel_sizer.Add(title,
                        border=5,
                        flag=wx.TOP | wx.BOTTOM | wx.LEFT)

        panel_sizer.Add(wx.StaticLine(self),
                        flag=wx.EXPAND)

        panel_sizer.Add(self.grid)

        self.SetSizer(panel_sizer)
        panel_sizer.Fit(self)

        self.Bind(wx.EVT_KEY_DOWN, self.on_enter)

    def on_enter(self, event):
        if event.GetKeyCode() == wx.WXK_RETURN or event.GetKeyCode() == \
                wx.WXK_NUMPAD_ENTER:

                if self.grid.GetGridCursorRow() == 3:
                    self.GetParent().move_to_next(2)

        event.Skip()

    def update_grid(self, values):
        for i, value in enumerate(values):
            self.grid.Table.SetValue(i, 0, value)

        msg = wx.grid.GridTableMessage(self.grid.Table,
                                       wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.grid.ProcessTableMessage(msg)


class MyMachineDataSource(wx.grid.PyGridTableBase):
    def __init__(self, data):
        super(MyMachineDataSource, self).__init__()

        self.data = data

    def GetNumberCols(self):
        return 2

    def GetNumberRows(self):
        return len(self.data)

    def GetValue(self, row, col):
        keys = {0: 'weights',
                1: 'amounts'}

        val = self.data[keys[col]][row]

        try:
            if col == 1 and np.isnan(val.amount):
                val = ''
        except:
            pass
        finally:
            return val

    def SetValue(self, row, col, value):
        if col == 0:
            Collection.set_value(self.data, row, value)

        msg = wx.grid.GridTableMessage(self.GetView().Table,
                                       wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.GetView().ProcessTableMessage(msg)

    def GetColLabelValue(self, col):
        cols = ['Weights (lb oz)', 'Amounts']

        return cols[col]

    def GetRowLabelValue(self, row):
        return self.data['names'][row]


class MyMetersDataSource(wx.grid.PyGridTableBase):
    def __init__(self, data):
        super(MyMetersDataSource, self).__init__()

        self.data = data

    def GetNumberCols(self):
        return 1

    def GetNumberRows(self):
        return len(self.data)

    def GetValue(self, row, col):
        val = self.data['readings'][row]

        try:
            if np.isnan(val):
                val = ''
        except:
            pass
        finally:
            return val

    def SetValue(self, row, col, value):
        self.data.set_value(row, 'readings', float(value))

    def GetColLabelValue(self, col):
        return 'Readings'

    def GetRowLabelValue(self, row):
        return self.data['meters'][row]


class MyChangersDataSource(wx.grid.PyGridTableBase):
    def __init__(self, data):
        super(MyChangersDataSource, self).__init__()

        self.data = data

    def GetNumberCols(self):
        return 2

    def GetNumberRows(self):
        return len(self.data)

    def GetValue(self, row, col):
        keys = {0: 'left',
                1: 'right'}

        val = self.data[keys[col]][row]

        try:
            if np.isnan(val):
                val = ''
            else:
                val = int(val)
        except:
            pass
        finally:
            return val

    def SetValue(self, row, col, value):
        keys = {0: 'left',
                1: 'right'}

        self.data.set_value(row, keys[col], float(value))

    def GetColLabelValue(self, col):
        # spaces to make columns larger
        labels = ['left    ', 'right   ']

        return labels[col]

    def GetRowLabelValue(self, row):
        return self.data['bills'][row]


class MyOthersDataSource(wx.grid.PyGridTableBase):
    def __init__(self, data):
        super(MyOthersDataSource, self).__init__()

        self.data = data

    def GetNumberCols(self):
        return 1

    def GetNumberRows(self):
        return len(self.data)

    def GetValue(self, row, col):
        val = self.data['amounts'][row]

        try:
            if np.isnan(val.amount):
                val = ''
        except:
            pass
        finally:
            return val

    def SetValue(self, row, col, value):
        self.data.set_value(row, 'amounts', Money(float(value)))

    def GetColLabelValue(self, col):
        return 'Amounts'

    def GetRowLabelValue(self, row):
        return self.data['labels'][row]


class MyGrid(wx.grid.Grid):
    """
    Class for custom grid.
    """
    def __init__(self, parent, data, source):
        super(MyGrid, self).__init__(parent)

        self.SetTable(source(data))
        self.AutoSizeColumns()


class PeriodPanel(wx.Panel):
    """
    Class for grid for a single period.
    """
    def __init__(self, parent, period_num):
        super(PeriodPanel, self).__init__(parent)

        self.frame = parent.GetTopLevelParent()

        self.period_num = period_num
        self.period_end = self.frame.col.period_dates[self.period_num]

        self.washer_grid = MyGrid(self,
            self.frame.list_panel.washer_period_dfs[period_num],
            MyMachineDataSource)

        self.dryer_grid = MyGrid(self,
            self.frame.list_panel.dryer_period_dfs[period_num],
            MyMachineDataSource)

        color = wx.Colour(220, 220, 220, 255)

        for i in range(2):
            for j in range(5, 11):
                self.washer_grid.SetCellBackgroundColour(j, i, color)
            for j in range(23, 28):
                self.washer_grid.SetCellBackgroundColour(j, i, color)

            for j in range(10, 16):
                self.dryer_grid.SetCellBackgroundColour(j, i, color)

        # panel sizer
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        panel_sizer.Add(self.washer_grid,
                        border=5,
                        flag=wx.RIGHT)
        panel_sizer.Add(self.dryer_grid)

        self.SetSizer(panel_sizer)

        self.Bind(wx.EVT_KEY_DOWN, self.on_enter)

    def on_enter(self, event):
        if event.GetKeyCode() == wx.WXK_RETURN or event.GetKeyCode() == \
                wx.WXK_NUMPAD_ENTER:

                if self.washer_grid.GetGridCursorRow() == 27:
                    self.washer_grid.GoToCell(0, 0)
                    self.dryer_grid.SetFocus()
                    self.dryer_grid.GoToCell(0, 0)

        event.Skip()


class MachinePanel(wx.Panel):
    """
    Panel with sheets of washers and dryers.
    """
    def __init__(self, parent):
        super(MachinePanel, self).__init__(parent)

        self.frame = parent.GetTopLevelParent()

        # notebook to hold panels
        self.machine_nb = wx.Notebook(self)

    def load_collection(self):

        periods = self.frame.col.num_periods

        self.period_panels = [PeriodPanel(self.machine_nb, i) for i in
                              range(periods)]

        while self.machine_nb.GetPageCount():
            self.machine_nb.DeletePage(0)

        for panel in self.period_panels:
            self.machine_nb.AddPage(panel, 'Period {} - {}'.format(
                panel.period_num + 1, panel.period_end.strftime('%m/%d/%y')))

        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        panel_sizer.Add(self.machine_nb)

        self.SetSizer(panel_sizer)
        panel_sizer.Fit(self)


class TopPanel(wx.Panel):
    """
    Panel holding the top row of panels.
    """
    def __init__(self, parent):
        super(TopPanel, self).__init__(parent)

        self.frame = parent.GetTopLevelParent()

        # panel sizer
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # panels
        self.meter_panel = MeterPanel(self)
        self.changer_panel = ChangerPanel(self)
        self.other_panel = OtherPanel(self)

        panel_sizer.Add(self.meter_panel,
                        flag=wx.EXPAND | wx.LEFT,
                        border=3)

        panel_sizer.Add(wx.StaticLine(self, style=wx.LI_VERTICAL),
                        flag=wx.LEFT | wx.RIGHT | wx.EXPAND,
                        border=5)

        panel_sizer.Add(self.changer_panel,
                        flag=wx.EXPAND)

        panel_sizer.Add(wx.StaticLine(self, style=wx.LI_VERTICAL),
                        flag=wx.LEFT | wx.RIGHT | wx.EXPAND,
                        border=5)

        panel_sizer.Add(self.other_panel,
                        flag=wx.EXPAND | wx.RIGHT,
                        border=3)

        self.SetSizer(panel_sizer)
        panel_sizer.Fit(self)

    def move_to_next(self, which):
        if which == 0:
            self.meter_panel.grid.GoToCell(0, 0)
            self.changer_panel.grid.SetFocus()
            self.changer_panel.grid.GoToCell(0, 0)

        if which == 1:
            self.changer_panel.grid.GoToCell(0, 0)
            self.other_panel.grid.SetFocus()
            self.other_panel.grid.GoToCell(0, 0)

        if which == 2:
            self.frame.machine_panel.period_panels[0].washer_grid.SetFocus()
            self.frame.machine_panel.period_panels[0].washer_grid.GoToCell(0, 0)


    def load_collection(self):
        self.meter_panel.update_grid(self.frame.col.df_meters['readings'])
        self.changer_panel.update_grid(self.frame.col.df_changers[['left',
                                                                   'right']])
        self.other_panel.update_grid(self.frame.col.df_others['amounts'])


class MyMenuBar(wx.MenuBar):
    """
    Class for custom menu bar.
    """
    def __init__(self, parent):
        super(MyMenuBar, self).__init__()

        self.frame = parent

        # menus
        file_menu = wx.Menu()

        # file menus
        file_new = file_menu.Append(wx.ID_NEW, '&New', 'New collection')
        file_save = file_menu.Append(wx.ID_SAVE, '&Save sheet',
                                     'Save collection')
        file_open = file_menu.Append(wx.ID_OPEN, '&Open MVL',
                                     'Open MVL Main')
        file_quit = file_menu.Append(wx.ID_EXIT, '&Quit', 'Quit application')

        # add top level menus to menu bar
        self.Append(file_menu, '&File')

        self.Bind(wx.EVT_MENU, self.on_file_new, file_new)
        self.Bind(wx.EVT_MENU, self.on_file_save, file_save)
        self.Bind(wx.EVT_MENU, self.on_file_open, file_open)
        # self.Bind(wx.EVT_MENU, self.on_file_quit, file_quit)

    def on_file_new(self, event):
        """
        Passes new call to frame.
        :param event:
        """
        self.frame.new_collection()

    def on_file_save(self, event):
        """
        Passes new call to frame.
        :param event:
        """
        self.frame.save_collection()
        self.frame.save_mvl()

    def on_file_open(self, event):
        """
        Passes new call to frame.
        :param event:
        """
        self.frame.load_mvl()


class MyCollectionDialog(wx.Dialog):
    def __init__(self, title):
        super(MyCollectionDialog, self).__init__(parent=None, title=title)

        week_end_label = wx.StaticText(self, label='Week end:')
        self.week_end_ctrl = wx.DatePickerCtrl(self)
        # week_end_ctrl.SetRange(wx.DateTime.Today(), wx.DateTime.Today())

        periods_label = wx.StaticText(self, label='Periods:')
        self.periods_ctrl = wx.SpinCtrl(self,
                                        min=1,
                                        initial=1,
                                        style=wx.SP_ARROW_KEYS)

        # inputs sizer
        self.inputs_sizer = wx.FlexGridSizer(rows=50, cols=2, vgap=5,
                                        hgap=5)

        self.inputs_sizer.Add(week_end_label,
                         border=4,
                         flag=wx.TOP)
        self.inputs_sizer.Add(self.week_end_ctrl)

        self.inputs_sizer.Add(periods_label,
                         border=4,
                         flag=wx.TOP)
        self.inputs_sizer.Add(self.periods_ctrl)

        self.period_date_ctrls = []
        self.period_date_labels = []

        for i in range(1):
            self.add_period_ctrl()

        self.dlg_sizer = wx.BoxSizer(wx.VERTICAL)

        self.dlg_sizer.Add(self.inputs_sizer,
                      proportion=0,
                      flag=wx.EXPAND | wx.TOP | wx.LEFT,
                      border=5)

        button_sizer = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        self.dlg_sizer.Add(button_sizer,
                      proportion=0,
                      flag=wx.EXPAND | wx.TOP | wx.BOTTOM,
                      border=10)

        self.SetSizer(self.dlg_sizer)
        self.dlg_sizer.Fit(self)

        self.Bind(wx.EVT_SPINCTRL, self.on_period_ctrl, self.periods_ctrl)

    def add_period_ctrl(self):
        num = len(self.period_date_ctrls) + 1
        label = '    Period {} end:'.format(num)
        label = wx.StaticText(self, label=label)

        ctrl = wx.DatePickerCtrl(self)

        self.period_date_labels.append(label)
        self.period_date_ctrls.append(ctrl)

        self.inputs_sizer.Add(label,
                              border=4,
                              flag=wx.TOP)
        self.inputs_sizer.Add(ctrl)

    def on_period_ctrl(self, event):
        periods = event.GetInt()
        ind = len(self.period_date_ctrls)
        if periods > ind:
            self.add_period_ctrl()

        else:
            childs = list(self.inputs_sizer.GetChildren())
            ind = len(childs) - 1

            self.inputs_sizer.Remove(ind)
            self.inputs_sizer.Remove(ind-1)

            self.period_date_ctrls[-1].Destroy()
            self.period_date_ctrls.pop(-1)
            self.period_date_labels[-1].Destroy()
            self.period_date_labels.pop(-1)

        self.dlg_sizer.Fit(self)
        self.Refresh()


class MyFrame(wx.Frame):
    """
    Class for generating main frame.
    """
    def __init__(self):
        super(MyFrame, self).__init__(None, title='MVL collections')

        self.col = None
        self.workbook = None

        # make calendar and list
        self.list_panel = ListPanel(self)
        self.calendar_panel = CalendarPanel(self)

        # calendar and list sizer
        calendar_list_sizer = wx.BoxSizer(wx.VERTICAL)

        calendar_list_sizer.Add(self.calendar_panel,
                                flag=wx.EXPAND)

        calendar_list_sizer.Add(self.list_panel,
                                proportion=1,
                                flag=wx.EXPAND)

        # make meter and notebook panel
        self.machine_panel = MachinePanel(self)
        self.top_panel = TopPanel(self)

        self.load_collection(empty_col)

        # last = self.list_panel.list_control.GetItemCount() - 1
        # col = self.list_panel.col_dict[self.list_panel.list_control.GetItemData(last)]
        # self.load_collection(col)

        # top and machine sizer
        top_machine_sizer = wx.BoxSizer(wx.VERTICAL)

        top_machine_sizer.Add(self.top_panel)
        top_machine_sizer.Add(wx.StaticLine(self),
                              border=5,
                              flag=wx.TOP | wx.BOTTOM | wx.EXPAND)
        top_machine_sizer.Add(self.machine_panel)

        # frame sizer
        frame_sizer = wx.BoxSizer(wx.HORIZONTAL)

        frame_sizer.Add(calendar_list_sizer,
                        flag=wx.EXPAND)

        frame_sizer.Add(top_machine_sizer,
                        flag=wx.EXPAND)

        # menu bar
        self.menu_bar = MyMenuBar(self)
        self.SetMenuBar(self.menu_bar)

        self.SetSizer(frame_sizer)
        frame_sizer.Fit(self)

        # change background color to match panels on win32
        self.SetBackgroundColour(wx.NullColour)

        self.Show()

    def load_collection(self, col):
        self.list_panel.load_collection(col)
        self.machine_panel.load_collection()
        self.top_panel.load_collection()

    def save_collection(self):
        # get rid of static lines
        panels = list(self.top_panel.GetChildren())[:-2]
        saves = [deepcopy(panel.grid.Table.data) for panel in panels]

        self.list_panel.save_collection(saves)

    def new_collection(self):
        """
        Creates new collection and adds to list.
        :return:
        """
        week_end, period_dates = self.new_collection_prompt()

        if week_end is None:
            return

        new_col = Collection(week_end, period_dates, washer_names, dryer_names)

        self.list_panel.add_collection(new_col)

    def new_collection_prompt(self):
        """
        Prompts for week end, num of periods, and period dates.
        :return:
        """
        dlg = MyCollectionDialog(title='Collection dates')

        # to exit out of dialog on cancel button
        if dlg.ShowModal() == wx.ID_CANCEL:
            return None, None

        dlg.Destroy()

        week_end = dlg.week_end_ctrl.GetValue().Format('%m/%d/%y')
        period_dates = [i.GetValue().Format('%m/%d/%y') for i in \
                        dlg.period_date_ctrls]

        return week_end, period_dates

    def load_mvl(self):
        path = self.load_mvl_prompt()
        self.workbook = os.path.abspath(path)
        new_cols = load_mvl_main(self.workbook)

        for col in sorted(new_cols, reverse=True):
            self.list_panel.add_collection(col, False)

    def load_mvl_prompt(self):
        """
        Prompts for dir of MVL main.
        """
        open_dialog = wx.FileDialog(self,
                                    message='Path to MVL main',
                                    wildcard='*.xlsx',
                                    style=wx.FD_OPEN)

        # to exit out of popup on cancel button
        if open_dialog.ShowModal() == wx.ID_CANCEL:
            return

        return open_dialog.GetPath()

    def save_mvl(self):
        """
        Saves collection to workbook.
        """
        if self.workbook is None:
            raise IOError('No workbook loaded to save to.')

        collection = self.list_panel.col
        workbook = self.workbook

        ind = self.list_panel.index_list.index(collection.week_end)
        previous_we = self.list_panel.index_list[ind - 1]

        save_to_mvl_main(workbook, previous_we, collection)



def main():
    """
    Main function to start GUI.
    """
    # instantiate app
    global app
    app = wx.App(False)
    # instantiate window
    frame = MyFrame()
    # run app
    app.MainLoop()

if __name__ == '__main__':
    main()