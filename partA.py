from typing import Iterable, override

from vacuumworld import run
from pyoptional.pyoptional import PyOptional
from vacuumworld.model.actions.vwactions import VWAction
from vacuumworld.model.actions.vwidle_action import VWIdleAction
from vacuumworld.model.actions.vwturn_action import VWTurnAction
from vacuumworld.model.actions.vwmove_action import VWMoveAction
from vacuumworld.model.actions.vwclean_action import VWCleanAction
from vacuumworld.model.actions.vwbroadcast_action import VWBroadcastAction
from vacuumworld.model.actions.vwspeak_action import VWSpeakAction
from vacuumworld.model.actions.vweffort import VWActionEffort
from vacuumworld.model.actor.mind.surrogate.vwactor_mind_surrogate import VWActorMindSurrogate


from vacuumworld.common.vwdirection import VWDirection
from vacuumworld.common.vwcolour import VWColour
from vacuumworld.common.vworientation import VWOrientation


class MyMind(VWActorMindSurrogate):

    def __init__(self) -> None:
        super(MyMind, self).__init__()

        # init Vars
        self.lastActionState = None
        self.actionState = "initial unsent"
        self.counter = 0
        self.boardLength = 0
        self.directionCurrent = VWOrientation.north
        self.targetLocation = None
        self.orangeDirt = []
        self.greenDirt = []
        self.otherAgents = []
        self.doneCleaning = True
        self.tellDirt = True
        self.currCleanColour = "white"

    @override
    def decide(self) -> Iterable[VWAction]:
        self.counter += 1

        # Send a message init yourself
        if self.actionState == "initial unsent":
            self.actionState = "initial"
            return[VWBroadcastAction(message = f"{self.get_own_colour()}", sender_id = self.get_own_id())]

        # if at end of board
        elif self.actionState == "boardLength" and self.get_latest_observation().is_wall_immediately_ahead() and self.get_own_orientation() == VWOrientation.east:
            self.boardLength = self.get_own_position().get_x()
            self.actionState = "scanning"

        #Send info after scanning map
        if self.actionState == "sendInfo":
            for n in self.otherAgents:
                if n[0] == "orange":
                    self.actionState = "sendInfoTwo"
                    return [VWSpeakAction(message = self.orangeDirt, recipients = [n[1]], sender_id = self.get_own_id())]
        elif self.actionState == "sendInfoTwo":
            for n in self.otherAgents:
                if n[0] == "green":
                    self.actionState = "cleaning"
                    return [VWSpeakAction(message = self.greenDirt, recipients = [n[1]], sender_id = self.get_own_id())]

        # code for when in cleaning mode
        if self.actionState == "cleaning":
            # Tell other agent that the dirt is being cleaned
            if self.tellDirt == False:
                self.tellDirt = True
                for n in self.otherAgents:
                    if n[0] == self.currCleanColour:
                        self.actionState = "cleaning"
                        print(f"I am cleaning {self.targetLocation} and it is {self.currCleanColour}")
                        return [VWSpeakAction(message = f"clean {self.targetLocation}", recipients = [n[1]], sender_id = self.get_own_id())]

            # if at target pos, clean the dirt
            if self.targetPosition():
                self.doneCleaning = True
                return [VWCleanAction()]

        # if two agents looking directly at each other, will turn away and move
        if self.actionState == "deadlock":
            if not self.get_latest_observation().is_wall_immediately_ahead() and not self.get_latest_observation().get_forward().get().has_actor():
                self.actionState = self.lastActionState
                return [VWMoveAction()]
            else:
                return [VWTurnAction(direction=VWDirection.right)]

        # Only done if there is a destination or if in the way of another agent
        if self.actionState != "waiting" and self.targetLocation is not None or self.actionState == "inWay":

            # if not looking correct direction, turn
            if self.get_own_orientation() != self.directionCurrent:
                return [VWTurnAction(direction=VWDirection.right)]

            # walking
            elif not self.get_latest_observation().is_wall_immediately_ahead() and not self.targetPosition() or not self.get_latest_observation().is_wall_immediately_ahead() and self.actionState == "inWay":

                # If there is an agent in the way, tell them to move
                if self.get_latest_observation().get_forward().get().has_cleaning_agent():
                    return [VWSpeakAction(message = f"inWay {self.get_own_position()} {self.get_latest_observation().get_forward().get().get_actor_appearance()}", recipients = [self.get_latest_observation().get_forward().get().get_actor_appearance().get().get_id()], sender_id = self.get_own_id())]

                # Otherwise, move
                return [VWMoveAction()]

        # waiting
        return [VWIdleAction()]

    @override
    def revise(self) -> None:
        print(f"Useful info: \nMy Colour: {self.get_own_colour()}\nMy Position: {self.get_own_position()}\nMy Action State: {self.actionState}")
        if self.get_own_colour() == VWColour.orange or self.get_own_colour() == VWColour.white:
            print(f"Orange Dirt: {self.orangeDirt}\n")
        if self.get_own_colour() == VWColour.green or self.get_own_colour() == VWColour.white:
            print(f"Green Dirt: {self.greenDirt}\n")
        # make sure agent doesn't get stuck getting out of other agent's ways
        if self.actionState == "inWay":
            self.counter += 1
            if self.counter >= 3:
                self.actionState = self.lastActionState
                self.counter = 0

        # Agents wait to receive messages initialising all other agents before going into waiting mode
        if self.actionState == "initial" and self.get_own_colour() != VWColour.white:
            self.counter += 1
            if self.counter >= 3:
                self.actionState = "waiting"
                self.counter = 0

        # What the white actor does
        if self.get_own_colour() == VWColour.white:
            # If in init stage and have no location, go to row 1 and then find the edge of the board
            if self.actionState == "initial":
                if self.targetLocation is None:
                    self.targetLocation = (self.get_own_position().get_x(), 1)

                elif self.targetPosition():
                    self.directionCurrent = VWOrientation.east
                    self.actionState = "boardLength"

            elif self.actionState == "boardLength":
                # if not at end of board, find end
                if not self.get_latest_observation().is_wall_immediately_ahead():
                    self.targetLocation = (self.targetLocation[0] + 1, 0)

                # when at end, set as board position and begin scanning
                elif self.get_latest_observation().is_wall_immediately_ahead() and self.get_own_orientation() == VWOrientation.east:
                    self.boardLength = self.get_own_position().get_x()
                    self.targetLocation = self.get_own_position()
                    self.actionState = "scanning"

            # scan the board
            elif self.actionState == "scanning" or self.actionState == "scanningLastRow":
                self.checkDirt()
                if self.targetPosition():
                    self.getNextScan()
                    if self.actionState == "scanningDone":
                        self.actionState = "sendInfo"

            # picks whichever has more dirt, or defaults to orange
            elif self.actionState == "cleaning":
                if self.targetPosition() or self.targetLocation == None:
                    # if done cleaning, pick longest list and clean from the end
                    if len(self.greenDirt) > 0 and len(self.greenDirt) > len(self.orangeDirt) and self.doneCleaning == True:
                        print ("clean green")
                        self.currCleanColour = "green"
                        self.doneCleaning = False
                        self.tellDirt = False
                        self.targetLocation = (int(self.greenDirt[len(self.greenDirt)-1][1]), int(self.greenDirt[len(self.greenDirt)-1][4]))
                        self.greenDirt.pop(len(self.orangeDirt)-1)
                    elif len(self.orangeDirt) > 0 and self.doneCleaning == True:
                        print("clean Orange")
                        self.currCleanColour = "orange"
                        self.doneCleaning = False
                        self.tellDirt = False
                        self.targetLocation = (int(self.orangeDirt[len(self.orangeDirt)-1][1]), int(self.orangeDirt[len(self.orangeDirt)-1][4]))
                        self.orangeDirt.pop(len(self.orangeDirt)-1)
                print(self.targetLocation)

        # Other colours
        else:
            # will go to next dirt in the list.
            if self.actionState == "cleaning":
                # if at the current position, or needs a location.
                if self.targetPosition() or self.targetLocation == None:
                    # if done cleaning, and respective colour's list isnt empty, pick new dirt to clean.
                    if self.get_own_colour() == VWColour.green and len(self.greenDirt) > 0 and self.doneCleaning == True:
                        self.doneCleaning = False
                        self.tellDirt = False
                        self.targetLocation = (int(self.greenDirt[0][1]), int(self.greenDirt[0][4]))
                        self.greenDirt.pop(0)

                    elif len(self.orangeDirt) > 0 and self.doneCleaning == True:
                        self.doneCleaning = False
                        self.tellDirt = False
                        self.targetLocation = (int(self.orangeDirt[0][1]), int(self.orangeDirt[0][4]))
                        self.orangeDirt.pop(0)

        # go through all the messages recieved
        if self.get_latest_received_messages() is not None:
            for m in self.get_latest_received_messages():
                # This will save the colour of the other agents and ID
                agentIn = False
                for a in self.otherAgents:
                    if m.get_sender_id() == a[1]:
                        agentIn = True
                if not agentIn:
                    self.otherAgents.append((m.get_content(), m.get_sender_id()))
                # This tells if the agent is in the way
                if m.get_content()[0:5] == "inWay":
                    self.getOutOfWay(self.get_own_position(), m.get_content()[6:12], self.get_own_orientation())
                # this is a message from another agent saying what colour they cleaned so it can be removed from list
                if m.get_content()[0:5] == "clean":
                    for u in self.otherAgents:
                        if m.get_sender_id() == u[1]:
                            if u[0] == "orange" or self.get_own_colour() == VWColour.orange:
                                if str(m.get_content()[6:12]) in self.orangeDirt:
                                    self.orangeDirt.remove(m.get_content()[6:12])
                            elif u[0] == "green" or self.get_own_colour() == VWColour.green:
                                if str(m.get_content()[6:12]) in self.greenDirt:
                                    self.greenDirt.remove(m.get_content()[6:12])

                # if waiting for map scan and message nothing else, take message as the dirt.
                elif self.actionState == "waiting":
                    if self.get_own_colour() == VWColour.green:
                        self.greenDirt = m.get_content()
                    else:
                        self.orangeDirt = m.get_content()
                    self.actionState = "cleaning"
                    self.lastActionState = "cleaning"

        # points the agent in correct direction for target location
        if self.actionState != "waiting" and self.targetLocation is not None:
            if not self.targetPosition() and self.actionState != "inWay":
                if self.get_own_position().get_x() > self.targetLocation[0]:
                    self.directionCurrent = VWOrientation.west
                elif self.get_own_position().get_x() < self.targetLocation[0]:
                    self.directionCurrent = VWOrientation.east
                elif self.get_own_position().get_y() > self.targetLocation[1]:
                    self.directionCurrent = VWOrientation.north
                elif self.get_own_position().get_y() < self.targetLocation[1]:
                    self.directionCurrent = VWOrientation.south

        pass

    # class that checks if the player is at the target location
    def targetPosition(self):
        if self.targetLocation is not None:
            if self.get_own_position().get_x() == self.targetLocation[0] and self.get_own_position().get_y() == self.targetLocation[1]:
                return True
        return False

    # class that manages getting next location for scanning
    def getNextScan(self):
        if self.actionState == "scanningLastRow":
            self.actionState = "scanningDone"
            return

        if self.get_own_position().get_y() == self.boardLength:
            self.actionState = "scanningLastRow"
            if self.get_own_position().get_x() == 0:
                self.targetLocation = (self.boardLength, self.get_own_position().get_y())
            else:
                self.targetLocation = (0, self.get_own_position().get_y())

        elif self.get_own_position().get_y() + 3 <= self.boardLength:
            if self.get_own_position().get_x() == 0:
                self.targetLocation = (self.boardLength, self.get_own_position().get_y() + 3)
            else:
                self.targetLocation = (0, self.get_own_position().get_y() + 3)

        elif self.get_own_position().get_y() + 2 <= self.boardLength:

            if self.get_own_position().get_x() == 0:
                self.targetLocation = (self.boardLength, self.get_own_position().get_y() + 2)
            else:
                self.targetLocation = (0, self.get_own_position().get_y() + 2)
        else:

            if self.get_own_position().get_x() == 0:
                self.targetLocation = (self.boardLength, self.get_own_position().get_y() + 1)
            else:
                self.targetLocation = (0, self.get_own_position().get_y() + 1)
        print(f"target: {self.targetLocation}\n board len: {self.boardLength}---------------------------------------------")


    # looks at all adjacent squares and checks for dirt and sorts it
    def checkDirt(self):
        toCheck = []
        if self.get_own_orientation() == VWOrientation.west:
            toCheck.append(self.get_latest_observation().get_right())
            if self.get_own_position().get_y() != self.boardLength:
                toCheck.append(self.get_latest_observation().get_left())
        elif self.get_own_orientation() == VWOrientation.east:
            toCheck.append(self.get_latest_observation().get_left())
            if self.get_own_position().get_y() != self.boardLength:
                toCheck.append(self.get_latest_observation().get_right())
        if not self.get_latest_observation().is_wall_immediately_ahead():
            toCheck.append(self.get_latest_observation().get_forward())

        toCheck.append(self.get_latest_observation().get_center())

        for m in toCheck:
            if str(m) != "PyOptional.empty()":
                if m.get().has_dirt():
                    if m.get().get_dirt_appearance().get().get_colour() == VWColour.orange:
                        if str(m.get().get_coord()) not in self.orangeDirt:
                            self.orangeDirt.append(str(m.get().get_coord()))
                    elif m.get().get_dirt_appearance().get().get_colour() == VWColour.green:
                        if str(m.get().get_coord()) not in self.greenDirt:
                            self.greenDirt.append(str(m.get().get_coord()))

        pass

    # class that manages getting out of agent's way
    def getOutOfWay(self, positionCurr, tempOtherPos, direction):
        if self.actionState == "deadlock":
            return
        otherPosition = (int(tempOtherPos[1]), int(tempOtherPos[4]))
        self.lastActionState = self.actionState
        self.actionState = "inWay"
        if not self.get_latest_observation().is_wall_immediately_ahead():
            if str(self.get_latest_observation().get_forward().get().get_coord()) == tempOtherPos:
                self.actionState = "deadlock"
                return

        if direction == VWOrientation.west and otherPosition[0] == positionCurr.get_x() + 1  or direction == VWOrientation.west and self.get_latest_observation().is_wall_immediately_ahead():
            self.directionCurrent = VWOrientation.north
        elif direction == VWOrientation.east and otherPosition[0] == positionCurr.get_x() - 1 or direction == VWOrientation.east and self.get_latest_observation().is_wall_immediately_ahead():
            self.directionCurrent = VWOrientation.south
        elif direction == VWOrientation.north and otherPosition[1] == positionCurr.get_y() + 1 or direction == VWOrientation.north and self.get_latest_observation().is_wall_immediately_ahead():
            self.directionCurrent = VWOrientation.east
        elif direction == VWOrientation.south and otherPosition[1] == positionCurr.get_y() - 1 or direction == VWOrientation.south and self.get_latest_observation().is_wall_immediately_ahead():
            self.directionCurrent = VWOrientation.west


'''
    # sends a tuple with closest wall coords
    def findClosestWall(self, positionCurr, temp):
        boardSize = int(temp[1]) + 1
        directionX = abs(positionCurr.get_x() - (boardSize/2))
        directionY = abs(positionCurr.get_y() - (boardSize/2))
        # check if it is closer on x or y then direction

        if directionX <= directionY: # move up/down
            if (positionCurr.get_y()) < boardSize/2:
                print("up")
                return (positionCurr.get_x(), 0)
            else:
                print("down")
                return (positionCurr.get_x(), boardSize)
        else: # move x
            print(positionCurr.get_y())
            print(boardSize/2)
            if (positionCurr.get_x()) < boardSize/2:
                print("left")
                return (0, positionCurr.get_y())
            else:
                print("right")
                return (boardSize, positionCurr.get_y())
'''

if __name__ == "__main__":
    run(default_mind=MyMind(), efforts=VWActionEffort.REASONABLE_EFFORTS)
