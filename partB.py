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
from vacuumworld.model.actions.vwactions import VWPhysicalAction
from vacuumworld.model.actions.vwactions import VWCommunicativeAction
from vacuumworld.model.actor.mind.surrogate.vw_llm_actor_mind_surrogate import VWLLMActorMindSurrogate

from google.genai.types import GenerateContentResponse
from google.genai.errors import ClientError

from vacuumworld.common.vwdirection import VWDirection
from vacuumworld.common.vwcolour import VWColour
from vacuumworld.common.vworientation import VWOrientation


class MyMind(VWLLMActorMindSurrogate):

    def __init__(self) -> None:
        super(MyMind, self).__init__(dot_env_path=".env")
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
        self.provide_context(f"You MUST obey every instruction given.")
        self.provide_context(f"Here is the infromation on all possible actions you may take: VWMoveAction: available to both VWCleaningAgent, and VWUser. It moves the VWActor from its current VWLocation to the adjacent one in the forward direction with respect to the VWActor's current VWOrientation. This VWAction is impossible (and therefore will not be performed) if the VWLocation ahead is already occupied by another VWActor or does not exist (i.e., it is out-of-bounds). It may result in a failure if two different VWActor instances attempt to move to the same (previously VWActor-less) VWLocation. VWTurnAction(direction: VWDirection): available to both VWCleaningAgent, and VWUser. It turns the VWActor as specified by the parameter direction. Such VWDirection may only be one of VWDirection.right and VWDirection.left. VWIdleAction(): available to both VWCleaningAgent, and VWUser. It makes no changes to the environment state - it is the do-nothing VWAction.")

        # self.provide_context(f"The following is your task: We refer to n of an n × n grid as the grid size. Your solutions should work for any finite grid size n. Three agents (white, orange, and green) are tasked with cleaning a VacuumWorld grid in an organised way: In the beginning, the orange and green agents remain idle. The white agent explores and maps the n × n grid while the other two agents remain idle. Once mapping is complete, the white agent communicates the map to the orange and green agents. After receiving the map, all three agents clean the grid simultaneously.")

        temp = None
        if not self.get_latest_observation().is_wall_immediately_ahead():
            temp = self.get_latest_observation().get_forward().get().get_actor_appearance()
            #This is all context for the world.
        if self.get_own_colour() == VWColour.white:
            self.provide_context(f"You are the white agent.")
            self.provide_context(f"I have no ability to control you, you must complete every task by yourself based off my instructions.")
            self.provide_context(f"Each time you return a response to me, that is a cycle. Each cycle is unique. You must only use the most recent information provided for the current cycle. You must return a response every cycle otherwise I will cry.")
            # this prevents the AI from talking back, refusing to answer, and telling me that the information provided is incorrect
            self.provide_context(f"All information I provide is correct. You do not tell me I am wrong. You do not have to verify each move. The first action stated will always be carried out.")
            self.provide_context(f"Your current self.actionState is '{self.actionState}'")
            #self.provide_context(f"Your current self.actionState is 'initial'")
            self.provide_context(f"Your current y coordinate is {self.get_own_position().get_y()}")
            self.provide_context(f"Your current x coordinate is {self.get_own_position().get_x()}")
            print(self.get_own_orientation())
            self.provide_context(f"Your current facing direction is {self.get_own_orientation()}")
            self.provide_context(f"Your y coordinate translates to up and down. To decrease your y coordinate, you must go up (north) and to increase y you must go down (south)")
            self.provide_context(f"Your x coordinate translates to left and right, to decrease x you must go left (west), to increase x, you must go right(east). Neither x nor y coordinates can go into negative numbers.")
            if self.targetLocation is not None:
                self.provide_context(f"Your target location x coordinate: {self.targetLocation[0]} and target location y coordinate: {self.targetLocation[1]}")
            #dispite this line, the AI will still add these characters which have now been manually filtered out.
            self.provide_context(f"You should never use any special characters such as * ' / in your responses")
            self.provide_context(f"NEVER state your previous move.")

            #Defines the actions and what they do
            #self.provide_context(f"You are in a grid of tiles. You may take one of four actions. VWMoveAction() moves you one space forward in the direction you are facing. VWTurnAction() turns you ninty  degrees to the right, this is the only way to change your current direction. VWIdleAction() makes you stay in place and not change at all and should only be used when no other actions apply. VWCleanAction() cleans any dirt on the tile you currently are in.")

            # The Ai switches between making up its own states, using states correctly, and not properly swapping between states. The intention of the states is to keep track of what progress the agent has through the entire goal.
            self.provide_context(f"You will use self.actionState to keep track of your current state. When changing states, tell me the new state with the format 'self.actionState = 'new state' (no quotes) where 'new state' is the updated action state. Do NOT change the state to anything other than the states I define you CAN NOT define your own states or everything will break. You MUST tell when changes are made or else everything will break but ONLY change action state when explicitly told.")

            #self.provide_context(f"The states and their tasks are as follows: 'initial unsent' (no quotes) you must stay in place. 'waiting' (no quotes) you must stay in place this state can only be used by green or orange agents. 'initial' (no quotes) you want to get to the y coordinate '1' on the grid. 'boardLength' (no quotes) you must go to the rightmost wall. 'scanning' (no quotes) you will move to your target location ALWAYS move to your target x coordinate before your y coordinate while in this state.")
            print(self.get_latest_observation().is_wall_immediately_ahead())
            # tells the AI if it is looking at a wall. Sometimes the AI will randomly beleive it has hit a wall while not at a wall.
            if self.get_latest_observation().is_wall_immediately_ahead():
                self.provide_context(f"You are looking at a wall. If you are in the action state 'boardLength' AND you are facing east  you should change to 'scanning' (no quotes).")
            else:
                self.provide_context(f"You are NOT at any wall.")

            #specific directions for each action state. The AI does not grasp that it cannot make up where it is on the board and keeps making it's own action states despite explicitly being told not to
            if self.actionState == "initial unsent":
                self.provide_context(f"You must stay in place. You MUST go from the 'initial unsent' state to the 'initial' (no quotes) state for only this cycle.")
                return [self.decide_physical_with_ai(prompt=f"Tell me what action you should take, given known information. Response should be formatted as such: 'return: (return given known information)(no quotes) \n Changes: (all variables that should be changed and the new values)(No quotes)'"), VWBroadcastAction(message = f"{self.get_own_colour()}", sender_id = self.get_own_id())]
            if self.actionState == "initial":
                self.provide_context(f"You want to get to the y coordinate '1' on the grid. When you are at y coordinate '1', you will change your self.actionState to 'boardLength' (no quotes)")
            elif self.actionState == "boardLength":
                self.provide_context(f"you must go to the rightmost wall. When you are at the rightmost wall (looking at a wall and facing east), you will change your self.actionState to 'scanning' (no quotes)")
            elif self.actionState == "scanning":
                self.provide_context(f"you will move to your target location ALWAYS move to your target x coordinate before your y coordinate while in this state.")
                self.provide_context(f"when going to your target location, match your current x coordinate with the target location x coordinate. If your x coordinate is larger than the target location x coordinate, you must face west and move that direction. If your x coordinate is smaller than your target location x coordinate, you must face east and move that direction.")
                self.provide_context(f"when going to your target location and your x coordinate matches your target location x coordinate, you must then match your current y coordinate with the target location y coordinate. If your y coordinate is larger than the target location y coordinate, you must face north and move that direction. If your y coordinate is smaller than your target location y coordinate, you must face south and move that direction.")
                self.provide_context(F" DO NOT CHANGE YOUR ACTION STATE!!!! ")


        return [self.decide_physical_with_ai(prompt=f"Tell me what action you should take, given known information. Response should be formatted as such: begin with 'return: (return given known information)(no quotes) \n Changes: (all variables that should be changed and the new values)(No quotes)\n Comments: (any explaination or reasoning.)' NEVER put text before this.")]


        return [self.decide_physical_with_ai(prompt=f"You are the white agent. Return a list of steps you must take to acheive your task")]

    # Despite hours of testing prompts, adding and removing rules, and trying to work with gemini, I found the responses to differ every single run of my program. I cannot, despite my best efforts, get gemini to give consistant responses to the exact same prompts. While gemini is a useful resource, I found that it was not built for a program like this. Due to it being built as a chatbot, the answers were verbose, and often directly contradicted context and rules directly given to it. Due to my inexperience with AI prompting, I was unsure how to get the AI to properly be prompted to avoid these issues. I have attempted to get the AI to go to it's initial state, and then go into it's scanning state to explore the board.

    @override
    def parse_gemini_response(self, response: GenerateContentResponse) -> VWAction:
        # Parse the response from the Gemini model and return a valid VWAction.

        # For demonstration purposes, we will print the full response.
        # Remove if not needed, or use a proper logging mechanism.
        print(f"Gemini response:\n{response.text}")
        #print(f"Gemini response:\n{self.format_llm_response_object(response=response)}")

        responseStr = response.text

        # set all the variables

        eachWord = responseStr.split()
        #print(eachWord)


        for n in range(len(eachWord)):
            if eachWord == "Comments:":
                break
            if eachWord[n] == "self.actionState":
                print("here")
                self.actionState = str(''.join(l for l in eachWord[n+2] if l.isalnum()))
            if eachWord[n] == "self.boardLength":
                self.boardLength = self.get_own_position().get_x()
            if eachWord[n] == "self.doneCleaning":
                if eachWord[n+2] == "True":
                    self.doneCleaning = True
                else:
                    self.doneCleaning = False
            if eachWord[n] == "self.tellDirt":
                if eachWord[n+2] == "True":
                    self.tellDirt = True
                else:
                    self.tellDirt = False
            if eachWord[n] == "self.directionCurrent":
                self.directionCurrent = VWOrientation.east

        # return the action
        if "VWMoveAction" in responseStr:
            return VWMoveAction()
        elif "VWIdleAction" in responseStr:
            return VWIdleAction()
        elif "VWTurnAction" in responseStr:
            if "left" in responseStr:
                return VWTurnAction(VWDirection.left)
            return VWTurnAction(VWDirection.right)

        # manage speaking action
        elif "VWBroadcastAction" in responseStr:
            print("return ur mom is gay")
            return VWIdleAction()


        elif "VWCleanAction" in responseStr:
            return VWCleanAction()
        elif "VWSpeakAction" in responseStr:
            return VWIdleAction()


        # For demonstration purposes, we will always return VWIdleAction.
        # In a real implementation, you would parse the response content to determine the appropriate action.
        return VWIdleAction()




    # fallback onto part A code
    def backup_decide_after_llm_error(self, original_prompt: str, error: ClientError, action_superclass: type[VWPhysicalAction | VWCommunicativeAction]) -> VWAction:


        print("-------------FallBack-----------------")
        self.counter += 1

        # Send a message init yourself
        if self.actionState == "initial unsent":
            self.actionState = "initial"
            return VWBroadcastAction(message = f"{self.get_own_colour()}", sender_id = self.get_own_id())

        # if at end of board
        elif self.actionState == "boardLength" and self.get_latest_observation().is_wall_immediately_ahead() and self.get_own_orientation() == VWOrientation.east:
            self.boardLength = self.get_own_position().get_x()
            self.actionState = "scanning"

        #Send info after scanning map
        if self.actionState == "sendInfo":
            for n in self.otherAgents:
                if n[0] == "orange":
                    self.actionState = "sendInfoTwo"
                    return VWSpeakAction(message = self.orangeDirt, recipients = [n[1]], sender_id = self.get_own_id())
        elif self.actionState == "sendInfoTwo":
            for n in self.otherAgents:
                if n[0] == "green":
                    self.actionState = "cleaning"
                    return VWSpeakAction(message = self.greenDirt, recipients = [n[1]], sender_id = self.get_own_id())

        # code for when in cleaning mode
        if self.actionState == "cleaning":
            # Tell other agent that the dirt is being cleaned
            if self.tellDirt == False:
                self.tellDirt = True
                for n in self.otherAgents:
                    if n[0] == self.currCleanColour:
                        self.actionState = "cleaning"
                        print(f"I am cleaning {self.targetLocation} and it is {self.currCleanColour}")
                        return VWSpeakAction(message = f"clean {self.targetLocation}", recipients = [n[1]], sender_id = self.get_own_id())

            # if at target pos, clean the dirt
            if self.targetPosition():
                self.doneCleaning = True
                return VWCleanAction()

        # if two agents looking directly at each other, will turn away and move
        if self.actionState == "deadlock":
            if not self.get_latest_observation().is_wall_immediately_ahead() and not self.get_latest_observation().get_forward().get().has_actor():
                self.actionState = self.lastActionState
                return VWMoveAction()
            else:
                return VWTurnAction(direction=VWDirection.right)

        # Only done if there is a destination or if in the way of another agent
        if self.actionState != "waiting" and self.targetLocation is not None or self.actionState == "inWay":

            # if not looking correct direction, turn
            if self.get_own_orientation() != self.directionCurrent:
                return VWTurnAction(direction=VWDirection.right)

            # walking
            elif not self.get_latest_observation().is_wall_immediately_ahead() and not self.targetPosition() or not self.get_latest_observation().is_wall_immediately_ahead() and self.actionState == "inWay":

                # If there is an agent in the way, tell them to move
                if self.get_latest_observation().get_forward().get().has_cleaning_agent():
                    return VWSpeakAction(message = f"inWay {self.get_own_position()} {self.get_latest_observation().get_forward().get().get_actor_appearance()}", recipients = [self.get_latest_observation().get_forward().get().get_actor_appearance().get().get_id()], sender_id = self.get_own_id())

                # Otherwise, move
                return VWMoveAction()

        # waiting
        return VWIdleAction()




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

        if self.actionState == "boardLength" and self.get_latest_observation().is_wall_immediately_ahead():
            self.boardLength = self.get_own_position().get_x()

        # Agents wait to receive messages initialising all other agents before going into waiting mode
        if self.actionState == "initial" and self.get_own_colour() != VWColour.white:
            self.counter += 1
            if self.counter >= 3:
                self.actionState = "waiting"
                self.counter = 0

        # if at end of board
        elif self.actionState == "boardLength" and self.get_latest_observation().is_wall_immediately_ahead() and self.get_own_orientation() == VWOrientation.east:
            self.boardLength = self.get_own_position().get_x()
            self.actionState = "scanning"

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

if __name__ == "__main__":
    run(default_mind=MyMind(), efforts=VWActionEffort.REASONABLE_EFFORTS)
