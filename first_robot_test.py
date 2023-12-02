from opentrons import robot
robot.connect(robot.get_serial_ports_list()[0])
robot.home()

# PART ONE
from opentrons.drivers.smoothie_drivers.v2_0_0 import player
p = player.SmoothiePlayer_2_0_0()   # the Player will save the GCode commmands
robot.set_connection('simulate_switches')  # set the Robot to simulate your commands
robot._driver.record_start(p)   # start recording to the Player

 

# PART TWO
from opentrons import containers, instruments
first_available_tip_slot = 'A1'
num_wells = 24

class SterilePipetting:
    def __init__(self, pipette, trash):
        self.pipette = pipette
        self.trash = trash
        self.trash_index = 0
        self.rehome_counter = 0

    def transfer(self, volume, source, destination, air_gap_volume=5, mix_before=False, mix_after=False):
        self._rehome_func()
        max_hold = (self.pipette.max_volume - air_gap_volume)
        self.pipette.pick_up_tip()
        if mix_before:
            self._mix_transfer(volume, max_hold, source, destination)
        else:
            self._simple_transfer(volume, max_hold, source, destination)

        if mix_after:
            self.pipette.mix(3, max_hold/2, destination)
            self.pipette.move_to(destination.top())
            self.pipette.blow_out()

        self.trash_tip(prior_destination=destination)

    def _rehome_func(self):
        self.rehome_counter += 1
        if self.rehome_counter >= 8:
            self.rehome_counter = 0
            robot.home()

    def _simple_transfer(self, volume, max_hold, source, destination):
        while volume > max_hold:
            self.pipette.aspirate(max_hold, source)
            self.pipette.air_gap(5)
            self.pipette.dispense(destination)
            self.pipette.blow_out()
            volume -= max_hold
        self.pipette.aspirate(volume, source)
        self.pipette.air_gap(5)
        self.pipette.dispense(destination)
        self.pipette.blow_out()

    def _mix_transfer(self, volume, max_hold, source, destination):
        while volume > max_hold:
            self.pipette.mix(3, max_hold/2, source)
            self.pipette.aspirate(max_hold, source)
            self.pipette.air_gap(5)
            self.pipette.dispense(destination)
            self.pipette.blow_out()
            volume -= max_hold
        self.pipette.mix(3, max_hold/2, source)
        self.pipette.aspirate(volume, source)
        self.pipette.air_gap(5)
        self.pipette.dispense(destination)
        self.pipette.blow_out()

    def trash_tip(self,prior_destination=None):
        if prior_destination != None:
            self.pipette.move_to(prior_destination.top())
            self.pipette.air_gap(15)
        self.pipette.drop_tip(self.trash[self.trash_index])
        self.trash_index += 1

robot.reset()
robot.head_speed(combined_speed=20000, x=20000, y=20000, z=2500) # [!WARN!] Stress Tested up to x=40k, y=40k, z=2.5k. ROBOT BREAKS AT z=5k

# containers
tiprack = containers.load('tiprack-200ul', 'A1')
cell_culture = containers.load('24-well-plate', 'C1')

imaging_plate = containers.load('96_flat_imaging','B1') # [!WARN!] This container doesn't exist by default. You'll need to upload "create_new_containers.py" to the OT-1 app at least once before uploading this protocol.
trash = containers.load('tiprack-200ul', 'D2') # [!INFO!] This is just a trash can. I suggest calibrating this to the middle of the container. It's only ever going to dispense in "A1"
stain = containers.load('tube-rack-2ml', 'B2') # [!INFO!] This is any type of media container you want, tube, trough, or bottle. It only ever draws from the point you calibrate. It's defined as a tube rack so that the tip clears the surface before drawing it's air gap.

# pipettes
pipette = instruments.Pipette(axis='b', max_volume=200, tip_racks=[tiprack])
pipette.starting_tip = tiprack.well(first_available_tip_slot)

# Initialize SterilePipetting instance
sterile_pipetting = SterilePipetting(pipette, trash)

robot.move_to(location=imaging_plate[0])

#PART THREE
robot._driver.record_stop()   # stop recording
robot.set_connection('live')  # set the connection to be the physical OT-One
robot._driver.play(p)         # save the GCode commands to the a file on the OT-One and start
