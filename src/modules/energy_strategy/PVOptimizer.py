##############################################################################################
# PVOptimizer
# Author: Gerard Mamelle (2024)
# Version : 1.1.0
# Program under MIT licence
#
# Release
# 1.1.0 Run with multiple Off peak periods
##############################################################################################
import hassapi as hass
import math
import datetime
from datetime import timedelta
from datetime import time
from dataclasses import dataclass
from typing import Dict

MAX_DEVICE = 8              # Maximum number of available devices
LOOP_INTERVAL = 60          # Interval in seconds to check devices


# Programme principal
class PVOptimizer(hass.Hass):

	def initialize(self):
		self.log("Start PVOptimizer")
		self.create_device_list()
		# check if entities exist, if not create missing entities
		self.check_switch_entities()
		# Grid contract subscription 
		self.contratHeuresCreuses = bool(self.args["subscription"] != 'Base')
		# off_peak indicator
		if self.contratHeuresCreuses:
		    self.off_peak = self.get_state(self.args["off_peak"])
		# init grid status 
		self.available_energy = 0
		# Init power ratio
		self.power_ratio = 1.0
	   
		# listen for grid of_peak status change
		if self.contratHeuresCreuses:
		    self.listen_state(self.change_off_peak,self.args["off_peak"])
		# schedule day initialization after tempo color change
		self.run_daily(self.init_day, "06:10:00")              
		# schedule day loop every 60 seconds
		self.run_every(self.day_loop, "now", 60)  

		# compute current power ratio 
		self.compute_power_ratio()
		# get grid power balance
		self.update_current_grid_status()

		self.log("PVOptimizer initialized")

	@property
	def color_tempo(self) -> str:
		list_colors = ["Bleu" , "Blanc", "Rouge"]
		try:
		    response = str(self.get_state(self.args["journee_tempo"]))
		    if response in list_colors:
		        return response
		    else:
		        self.log("Bad argument for journee_tempo, Rouge applied") 
		        return "Rouge"    

		except Exception as e:
		    self.log("missing required argument: couleur journee tempo", e)
		    return "Rouge"

	@property
	def subscription(self) -> str:
		list_subscriptions = ["Tempo", "HeuresCreuses", "Base"]
		try:
		    response = str(self.args["subscription"])  
		    if response in list_subscriptions:
		        return response
		    else:
		        self.log("Bad argument for subscription, Base subscription applied") 
		        return "Base"    
		except Exception as e:
		    self.log("missing required argument: subscription", e)
		    return "Base"

	# Main loop to check devices every LOOP_INTERVAL seconds
	# Only active during day light and "jours bleus et blancs"
	def day_loop(self, kwargs):                                 
		if self.now_is_between("sunrise", "sunset"):
		    if self.subscription == "Tempo":
		        if self.color_tempo == "Rouge":
		            return 
		    # update device process status
		    self.update_process() 
		    # update available pv power                        
		    self.available_energy = self.update_current_grid_status()             
		    # try to init new device request
		    self.try_init_new_process()               

	def init_day(self, kwargs):                             
		self.log("Init day")
		self.reset_all_devices()
		self.compute_power_ratio()
		 
	# Change off peak status 
	def change_off_peak(self, entity, attribute, old_state, new_state, kwargs):
		if not self.contratHeuresCreuses:
		    return
		self.log(f'Off peak = {new_state}')
		self.off_peak = new_state
		if self.off_peak == 'on':
		    self.run_remaining_tasks()

	# Reinit all request and start commands at sunrise
	def reset_all_devices(self):
		for cur_device in self.device_list:
		    device_switch_status = self.get_state(cur_device.switch_entity)
		    if device_switch_status == 'on':
		        self.turn_off(cur_device.switch_entity)
		        self.log(f'switch {cur_device.name} off')
		    self.set_state(cur_device.enable_entity, state="off")
		    self.set_state(cur_device.start_entity, state="off")
		    cur_device.request = 'off'
		    cur_device.started = 'off'

	# fill device list with each device described in SolarOptimizer.yaml file
	def create_device_list(self) :
		i = 1
		for val in self.mydevs.values():
		    self.device_list.append(device(val.name,str(i),val.power,val.duration,val.switch_entity,val.night_time_on))
		    i = i + 1
		    if i > MAX_DEVICE:
		        self.log(f'Warning device number exceed {MAX_DEVICE}')
		        break
		
	# For each device check if device list entities are present and create them if necessary
	def check_switch_entities(self):
		if not self.device_list:
		    self.log('Warning missing my_devices item in yaml file')
		    return
		for cur_device in self.device_list:
		    if self.get_state(cur_device.switch_entity) == None:
		        self.log(f'Warning switch : {cur_device.switch_entity} doesn t exist')

	# update device process : switch push command, end of task
	def update_process(self):                        
		for cur_device in self.device_list:
		    cur_device.request = self.get_state(cur_device.enable_entity)  # update device enable
		    #self.log (f'state {cur_device.enable_entity} = {cur_device.request}')
		    device_switch_status = self.get_state(cur_device.switch_entity)
		    # Take in account direct start or stop device command with switch push
		    # update device status if necessary 
		    if device_switch_status == 'on':
		        if cur_device.request == 'off' or cur_device.started == 'off':
		            # device directly started with switch push
		            self.set_state(cur_device.enable_entity, state="on")
		            self.set_state(cur_device.start_entity, state="on")
		            cur_device.request = 'on'
		            cur_device.started = 'on'              
		            cur_device.start_time = self.get_now()
		            cur_device.task_duration = 0
		    else:
		        if cur_device.started == 'on':
		            # Device directly stopped with switch push
		            self.set_state(cur_device.enable_entity, state="off")
		            self.set_state(cur_device.start_entity, state="off")
		            cur_device.request = 'off'
		            cur_device.started = 'off'              
		        self.update_task_duration(cur_device)
		    # Check if current started devices need to be stopped
		    if cur_device.started == 'on':                                              
		        self.update_task_duration(cur_device)
		        self.check_end_process(cur_device)

	# Try to init new device
	def try_init_new_process(self):                                              
		for cur_device in self.device_list:
		    if cur_device.request == 'on' and cur_device.started == 'off':
		        if self.try_to_run(cur_device):
		            self.log(f'Start {cur_device.name}')
		 
	# Stop a device
	def stop_device(self, cur_device):
		self.log(f'Stop {cur_device.name}')
		self.set_state(cur_device.enable_entity, state="off")
		self.set_state(cur_device.start_entity, state="off")
		cur_device.request = 'off'
		cur_device.started = 'off'  
		self.update_task_duration(cur_device)
		# check if cur_device is a switch (night_time_on = None) 
		# or an application (night_time_on = !None)
		if cur_device.night_time_on != 'None':
		    # switch
		    self.turn_off(cur_device.switch_entity)
		    self.log(f'switch {cur_device.name} off')
		else:
		    # application
		    self.log(f'flag {cur_device.name} off')

	# Start a device
	def start_device(self, cur_device):
		self.log(f'Start {cur_device.name}')
		cur_device.started = 'on'
		cur_device.start_time = self.get_now()
		self.update_task_duration(cur_device)
		if cur_device.night_time_on != 'None':
		    self.turn_on(cur_device.switch_entity)
		    self.log(f'switch {cur_device.name} actif')
		else:
		    self.set_state(cur_device.start_entity, state="on")
		    self.log(f'Flag {cur_device.name} actif')

	# start device for night run
	def start_delayed_device(self,kwargs):
		entity_id = kwargs.get('entity_id')
		self.log(f'Start delayed service {entity_id}')
		self.turn_on(entity_id)

	# Stop device if min duration is reached
	def check_end_process(self, cur_device):
		if cur_device.task_duration > cur_device.min_duration:   
		    self.stop_device(cur_device)
		    self.log(f'Stop {cur_device.name} , duration = {cur_device.task_duration}')

	# Update grid balance
	def update_current_grid_status(self) -> int:
		available_energy = self.get_safe_float("available_energy")
		if available_energy == None:
		    return 0
		else:
		    return int(available_energy)
		
	# Try to start a device if available grid energy is 
	def try_to_run(self, cur_device) -> bool:
		power_mini = float(cur_device.power) * self.power_ratio
		power_mini = round(power_mini,1)
		# self.log(f'power mini  = {power_mini}, available power = {self.available_energy}')
		if power_mini < float(self.available_energy):
		    self.log(f'init start {cur_device.name}')
		    self.start_device(cur_device)
		    return True
		else:
		#    self.log(f'device power {cur_device.name} is too high, waiting !')
		    return False

	# Call night schedule time for those tasks who were not executed during the day 
	def run_remaining_tasks(self):
		self.log("Program HC Tasks")
		for cur_device in self.device_list:
		    cur_device.request = self.get_state(cur_device.enable_entity)            
		    if cur_device.request == 'on' and cur_device.night_time_on != 'None':
		        if self.now_is_between("13:00:00", "19:00:00") and self.now_is_between("13:00:00", "19:00:00", None, cur_device.night_time_on):
		            self.run_at(self.start_delayed_device,cur_device.night_time_on, entity_id=cur_device.switch_entity )
		            self.log(f' {cur_device.name} scheduled')
		        if self.now_is_between("19:00:01", "07:00:00") and self.now_is_between("19:00:01", "07:00:00", None, cur_device.night_time_on):
		            self.run_at(self.start_delayed_device,cur_device.night_time_on, entity_id=cur_device.switch_entity )
		            self.log(f' {cur_device.name} scheduled')

	# Check if min duration is reached
	def check_min_duration_ok(self, cur_device) -> bool:            
		return (bool(cur_device.task_duration > cur_device.min_duration)) 

	# Get delay in minutes between 2 times
	def get_delay_minutes(self,recent: datetime, old: datetime) -> int:
		diff = recent - old
		minutes = diff.total_seconds() / 60
		return int(minutes)

	# Update task duration if device is started otherwise reset duration
	def update_task_duration(self, cur_device):
		if cur_device.started == 'on':
		    cur_device.task_duration = self.get_delay_minutes(self.get_now(), cur_device.start_time)
		else:
		    cur_device.task_duration = 0
		self.set_state(cur_device.duration_entity, state=str(cur_device.task_duration))

	# Get a safe float state value for an entity.
	# Return None if entity is not available
	def get_safe_float(self, entity_id: str) -> float:			
		state = self.get_state(self.args[entity_id])
		if not state or state == "unknown" or state == "unavailable":
		    return None
		float_val = float(state)
		return None if math.isinf(float_val) or not math.isfinite(float_val) else float_val


	def getSellPrice(self):
		return self.args['prix_rachat']
	def getOffpeakPrice(self):
		key = 'prix_'+(self.color_tempo.lower())+'_hc'
		return self.args[key]
	def getPeakPrice(self):
		key = 'prix_'+(self.color_tempo.lower())+'_hp'
		return self.args[key]
	
	# @return: lower is the ratio, more it is interesting to use offpeak times
	def getPowerRatioOffpeak(self):
		sell_price = self.getSellPrice()
		offpeak_price = self.getOffpeakPrice()
		peak_price = self.getPeakPrice()
		self.power_ratio = (offpeak_price-sell_price) / (peak_price-sell_price)

	# @return: highter is the ratio, more it is interesting to use offpeak times
	def getPriceGrid(self):
		


