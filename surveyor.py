import socket
import sys
import time

import helper as hlp


class Surveyor:

    def __init__(self, host='192.168.0.50', port=8003):
        self.host = host
        self.port = port

    def __enter__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(5)  # Set a timeout for the connection
        except socket.error as e:
            print(f"Error connecting to {self.host}:{self.port} - {e}")
        return self

    def __exit__(self, *args):
        self.socket.close()

    def send(self, msg):
        msg = hlp.create_nmea_message(msg)
        try:
            self.socket.send(msg.encode())
            time.sleep(0.001)
        except socket.error as e:
            print(f"Error sending message - {e}")

    def receive(self, bytes=1024):
        try:
            time.sleep(0.01)
            data = self.socket.recv(bytes)
            if not data:
                print("Connection closed by the server.")
            return data.decode('utf-8')
        except socket.timeout:
            print("Socket timeout.")
        except socket.error as e:
            print(f"Error receiving data - {e}")

    def set_standby_mode(self):
        msg = "PSEAC,L,0,0,0,"
        self.send(msg)

    # thrust and thrust_diff must be an integer between -100 and 100
    # negative means backwards/counter_clockwise

    def set_thruster_mode(self, thrust, thrust_diff):
        msg = f"PSEAC,T,0,{int(thrust)},{int(thrust_diff)},"
        self.send(msg)

    def set_station_keep_mode(self):
        msg = "PSEAC,R,,,,"
        self.send(msg)

    # degrees = be an integer between 0 and 360
    def set_heading_mode(self, thrust, degrees):
        msg = f"PSEAC,C,{int(degrees)},{int(thrust)},,"
        self.send(msg)

    def set_waypoint_mode(self):
        msg = "PSEAC,W,0,0,0,"
        self.send(msg)

    def set_erp_mode(self):
        msg = "PSEAC,H,0,0,0,"
        self.send(msg)

    def start_file_download_mode(self, num_lines):
        msg = "PSEAC,F," + str(num_lines) + ",000,000,"
        self.send(msg)

    def end_file_download_mode(self):
        msg = "PSEAC,F,000,000,000"
        self.send(msg)

    def send_way_points(self, df, throttle, er_point_message):
        # Commands list to store all commands
        commands = []

        # df = hlp.create_way_point_messages_df(filename, False)

        # Start with the PSEAR command
        psear_cmd = "PSEAR,0,000,{},0,000".format(throttle)
        psear_cmd_with_checksum = hlp.create_nmea_message(psear_cmd)
        commands.append(psear_cmd_with_checksum)
        commands.append(er_point_message)

        # Generate OIWPL commands from the DataFrame
        oi_wpl_cmds = df['nmea_message'].tolist()
        commands.extend(oi_wpl_cmds)

        for cmd in commands:
            self.send(cmd)

    def get_control_mode_data(self):
        """
        Get control mode data from the Surveyor connection object.

        Parameters:
            s: The Surveyor connection object.

        Returns:
            Control mode string.
        """
        control_mode = None
        while not control_mode:
            control_mode = hlp.get_control_mode(self.receive())

        return control_mode

    def get_gps_coordinates(self):
        """
        Get GPS coordinates from the Surveyor connection object.

        Parameters:
            s: The Surveyor connection object.

        Returns:
            Tuple containing GPS coordinates.
        """
        coordinates = None
        gga_message = None
        while (coordinates == None) or (gga_message == None):
            gga_message = hlp.get_gga(self.receive())
            coordinates = hlp.get_coordinates(gga_message)

        return coordinates

    def get_attitude(self):
        """
        Get Attitude information from the Surveyor connection object.

        Parameters:
            s: The Surveyor connection object.

        Returns:
            Tuple containing heading.
        """
        heading = None
        attitude_message = None
        while (heading == None) or (attitude_message == None):
            attitude_message = hlp.get_attitude_message(self.receive())
            heading = hlp.get_heading(attitude_message)

        return heading
