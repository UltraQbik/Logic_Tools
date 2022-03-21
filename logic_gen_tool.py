import os
import json

# Gets the path to current folder
DATA_PATH = os.path.dirname(os.path.abspath(__file__)) + ('\\' if os.name == 'nt' else '/')


class LogicGate:
    """ Class that holds logic gate info """
    position: tuple
    mode: int
    color: str
    connections: list[int]

    def __init__(self, position: tuple = (0, 0, 0), mode: str = "and", color: str = "eeeeee"):
        self.position = position
        self.mode = {"and": 0, "or": 1, "xor": 2, "nand": 3, "nor": 4, "xnor": 5}.get(mode.lower(), 0)
        self.color = color
        self.connections = []

    def connect_to(self, id_: int):
        """ Adds controller to the logic gate """
        self.connections.append(id_)


class Circuit:
    """ Class that holds logic circuit, and does operations to them """
    logic_gates: list[LogicGate]
    index_lut: dict[int, dict]
    id_counter: int

    def __init__(self):
        self.logic_gates = []
        self.index_lut = {}
        self.id_counter = 0

    def is_solid(self, position: tuple) -> bool:
        """ Checks if the block exists """
        px, py, pz = position
        if self.index_lut.get(px) is None:
            return False
        if self.index_lut[px].get(py) is None:
            return False
        if self.index_lut[px][py].get(pz) is None:
            return False
        return True

    def get_block(self, position: tuple) -> int:
        """ Returns block """
        px, py, pz = position
        return self.index_lut.get(px, {}).get(py, {}).get(pz)

    def generate_lut(self, position: tuple) -> None:
        """ Generates look-up table for given position """
        px, py, pz = position
        if self.index_lut.get(px) is None:
            self.index_lut[px] = {}
        if self.index_lut[px].get(py) is None:
            self.index_lut[px][py] = {}
        if self.index_lut[px][py].get(pz) is None:
            self.index_lut[px][py][pz] = self.id_counter
        self.id_counter += 1

    def add_logic(self, logic_gate: LogicGate) -> None:
        """ Adds new logic gate """
        self.logic_gates.append(logic_gate)
        self.generate_lut(logic_gate.position)

    def wire_gates(self, input_pos: list, output_pos: list) -> None:
        """ Connects multiple gates together """
        if len(input_pos) == len(output_pos):
            for index in range(len(input_pos)):
                if not (self.is_solid(input_pos[index]) and self.is_solid(output_pos[index])):
                    continue
                self.logic_gates[self.get_block(input_pos[index])].connect_to(self.get_block(output_pos[index]))
        elif len(input_pos) == 1:
            if not self.is_solid((input_pos[0])):
                return None
            for index in range(len(output_pos)):
                if not self.is_solid(output_pos[index]):
                    continue
                self.logic_gates[self.get_block(input_pos[0])].connect_to(self.get_block(output_pos[index]))
        elif len(output_pos) == 1:
            if not self.is_solid((output_pos[0])):
                return None
            for index in range(len(input_pos)):
                if not self.is_solid(input_pos[index]):
                    continue
                self.logic_gates[self.get_block(input_pos[index])].connect_to(self.get_block(output_pos[0]))
        else:
            raise Exception("Unmatched amount of inputs and outputs!")

    def to_blueprint(self):
        """ Converts logic circuit to Scrap Mechanic blueprint file """
        childs = []
        for index, logic in enumerate(self.logic_gates):
            px, py, pz = logic.position
            connections = [{"id": id_} for id_ in logic.connections]
            childs.append({"color": logic.color,
                           "controller": {"active": False, "controllers": connections,
                                          "id": index, "joints": None, "mode": logic.mode},
                           "pos": {"x": px, "y": py, "z": pz},
                           "shapeId": "9f0f56e8-2c31-4d83-996c-d00a9b296c3f", "xaxis": 1, "zaxis": -2})
        return json.dumps({"bodies": [{"childs": childs}], "version": 3}, indent=2)


# Decoder creation
def create_decoder(address_bit_width: int = 8) -> Circuit:
    decoder = Circuit()
    n = 2 ** address_bit_width
    for oy in range(address_bit_width):
        decoder.add_logic(LogicGate((0, oy, 0), "and", "eeee22"))
        decoder.add_logic(LogicGate((1, oy, 0), "and", "222222"))
        decoder.add_logic(LogicGate((2, oy, 0), "nor", "222222"))
        decoder.wire_gates([(0, oy, 0)], [(1, oy, 0), (2, oy, 0)])
    index = 0
    split = n // round(address_bit_width - 0.5)
    for ox in range(split + 2, 2, -1):
        for oy in range(n//split):
            decoder.add_logic(LogicGate((ox, oy, 0), "and", "222222"))
            number = (address_bit_width - len(bin(index)[2:])) * "0" + bin(index)[2:]
            decoder.wire_gates([(1+int(char), address_bit_width-off-1, 0) for off, char in enumerate(number)],
                               [(ox, oy, 0)])
            index += 1
    return decoder


def square_func(index: int, bit_width: int):
    n = index ** 2
    return (bit_width - len(bin(n)[2:])) * "0" + bin(n)[2:]


# Creates look-up table for given function
def create_lut(address_bit_width: int = 8, output_bit_width: int = 8, str_function=square_func):
    lut = create_decoder(address_bit_width)
    n = 2 ** address_bit_width
    for oy in range(address_bit_width, address_bit_width+output_bit_width):
        lut.add_logic(LogicGate((0, oy, 0), "or", "22ee22"))
    index = 0
    split = n // round(address_bit_width - 0.5)
    for ox in range(3, split + 3):
        for oy in range(n // split - 1, -1, -1):
            func = str_function(index, output_bit_width)[::-1]
            outputs = []
            for off, char in enumerate(func, output_bit_width):
                if char == "1":
                    outputs.append((0, off-address_bit_width, 0))
            lut.wire_gates([(ox, oy, 0)], outputs)
            index += 1
    return lut


# Purely here for testing
def main():
    with open(DATA_PATH+"blueprint.json", "w", encoding="utf-8") as blueprint:
        blueprint.write(create_lut(8, 16).to_blueprint())


main()
