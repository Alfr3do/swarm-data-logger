import csv
import datetime
import math
import os
import sys

from geopy.distance import geodesic
import pynmea2

#import numpy as np
import pandas as pd


def create_grad_eval_coordinates(lat, lon, side_length):
    """
    Create coordinates for gradient evaluation given side distance around a GPS coordinate.

    Parameters:
    lat (float): Latitude of the center point.
    lon (float): Longitude of the center point.
    side_length (float): Length of the side of the square in meters.

    Returns:
    List[tuple]: A list of tuples representing the GPS coordinates of two corners of the square.
    """
    half_diagonal = (side_length / math.sqrt(2)) / 1000  # Convert meters to kilometers

    # Calculate the coordinates of the two corners
    top_left = geodesic(kilometers=half_diagonal).destination((lat, lon), bearing=315)
    top_right = geodesic(kilometers=half_diagonal).destination((lat, lon), bearing=45)
    #bottom_left = geodesic(kilometers=half_diagonal).destination((lat, lon), bearing=225)
    #bottom_right = geodesic(kilometers=half_diagonal).destination((lat, lon), bearing=135)

    return [(top_left.latitude, top_left.longitude),
            (top_right.latitude, top_right.longitude)]


def create_square_coordinates(lat, lon, side_length):
    """
    Create a square with a given side length around a GPS coordinate.

    Parameters:
    lat (float): Latitude of the center point.
    lon (float): Longitude of the center point.
    side_length (float): Length of the side of the square in meters.

    Returns:
    List[tuple]: A list of tuples representing the GPS coordinates of the four corners of the square.
    """
    half_diagonal = (side_length / math.sqrt(2)) / 1000  # Convert meters to kilometers

    # Calculate the coordinates of the four corners
    top_left = geodesic(kilometers=half_diagonal).destination((lat, lon), bearing=315)
    top_right = geodesic(kilometers=half_diagonal).destination((lat, lon), bearing=45)
    bottom_left = geodesic(kilometers=half_diagonal).destination((lat, lon), bearing=225)
    bottom_right = geodesic(kilometers=half_diagonal).destination((lat, lon), bearing=135)

    return [(top_left.latitude, top_left.longitude),
            (top_right.latitude, top_right.longitude),
            (bottom_right.latitude, bottom_right.longitude),
            (bottom_left.latitude, bottom_left.longitude)]


def are_coordinates_close(coord1, coord2, tolerance_meters=2):
    """
    Check if two coordinates are close enough based on a tolerance in meters.

    Parameters:
        coord1: Tuple containing first set of coordinates (latitude, longitude).
        coord2: Tuple containing second set of coordinates (latitude, longitude).
        tolerance_meters: Maximum allowed distance in meters between the two coordinates.

    Returns:
        Boolean indicating if the two coordinates are close enough.
    """
    distance = geodesic(coord1, coord2).meters
    return distance <= tolerance_meters


def append_tuple_to_csv(data_tuple, post_fix="", cols=["latitude", "longitude", "noisy latitude", "noisy longitude"]):
    # Get today's date in the "YYYYMMDD" format
    today_date = datetime.date.today().strftime("%Y%m%d")

    # Create the "out" directory if it doesn't exist
    out_dir = "out"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # Define the CSV file path using today's date
    file_path = os.path.join(out_dir, f"{today_date+post_fix}.csv")

    # Check if the file already exists, and create it with headers if it doesn't
    if not os.path.isfile(file_path):
        with open(file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(cols)

    # Append the data_tuple to the CSV file
    with open(file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(data_tuple)


def add_laplace_to_tuple(input_tuple, epsilon=1000000):
    # Create Laplacian noise with the same shape as the input tuple
    #noise = np.random.laplace(scale=1 / epsilon, size=len(input_tuple))

    # Add noise to each element in the input tuple
    #noisy_tuple = tuple(input_val + noise_val for input_val, noise_val in zip(input_tuple, noise))
    noisy_tuple = 0
    return noisy_tuple


def get_message_by_prefix(message, prefix):
    """Find the message in the split list that starts with the given prefix."""
    messages = message.split('\r\n')
    for msg in messages:
        if msg.startswith(prefix):
            return msg
    return None


def get_gga(message):
    """Extract the GPGGA message."""
    gga = get_message_by_prefix(message, '$GPGGA')
    if gga:
        return gga
    return None

def get_attitude_message(message):
    """Extract the PSEAA message."""
    attitude = get_message_by_prefix(message, '$PSEAA')
    if attitude:
        return attitude
    return None


def get_control_mode(message):
    """Extract the PSEAD message and determine the control mode."""
    psead = get_message_by_prefix(message, '$PSEAD')
    if psead:
        psead = psead.split(',')
        code = psead[1]

        switch_dict = {
            'L': 'Standby',
            'T': 'Thruster',
            'C': 'Heading',
            'G': 'Speed',
            'R': 'Station Keep',
            'N': 'River Nav',
            'W': 'Waypoint',
            'I': 'Autopilot',
            '3': 'Compass Cal',
            'H': 'Go To ERP',
            'D': 'Depth',
            'S': 'Gravity Vector Direction',
            'F': 'File Download',
            '!': 'Boot Loader'
        }
        return switch_dict.get(code, 'Unknown')
    return None


def get_timestamp(gga_message):
    try:
        gga = pynmea2.parse(gga_message)

        if isinstance(gga, pynmea2.GGA):
            # Use the attributes provided by pynmea2
            return gga.timestamp

    except pynmea2.ParseError:
        pass
    except ValueError:
        pass
    except TypeError:
        pass

    return None

def get_coordinates(gga_message):
    try:
        gga = pynmea2.parse(gga_message)

        if isinstance(gga, pynmea2.GGA):
            # Use the attributes provided by pynmea2
            latitude_nmea = gga.latitude
            longitude_nmea = gga.longitude

            return latitude_nmea, longitude_nmea

    except pynmea2.ParseError:
        pass
    except ValueError:
        pass
    except TypeError:
        pass

    return None


def get_heading(attitude_message):
    try:
        message_parts = attitude_message.split(',')
        if len(message_parts)>=4:
            heading = float(message_parts[3])
            return heading
        else:
            print("Invalid message format")
    except ValueError:
        pass
    except TypeError:
        pass

    return None


def save(coordinates, exo2_data, add_noise=True):
    """
    Process the coordinates and Exo2 data, add noise (if required), and append to CSV.

    Parameters:
        coordinates: Tuple containing GPS coordinates.
        exo2_data: List of data from Exo2 sensor.
        add_noise: Boolean indicating whether to add Laplace noise to the coordinates.

    Returns:
        None
    """
    combined_data = coordinates + tuple(exo2_data)
    gps_cols = ["latitude", "longitude"]
    noisy_gps_cols = ["noisy latitude", "noisy longitude"]
    data_cols = ["date", "time", "odo (%sat)", "odo (mg/l)" , "temp (c)", "cond (us/cm)", "salinity (ppt)", "pressure (psia)", "depth (m)"]

    if combined_data:
        if add_noise:
            noisy_coordinates = add_laplace_to_tuple(coordinates)
            append_tuple_to_csv(combined_data + noisy_coordinates, cols=gps_cols + data_cols + noisy_gps_cols)
        else:
            append_tuple_to_csv(combined_data, post_fix="_continuous", cols=gps_cols + data_cols)


def compute_nmea_checksum(message):
    """Compute the checksum for an NMEA message."""
    checksum = 0
    for char in message:
        checksum ^= ord(char)
    return '{:02X}'.format(checksum)


def convert_lat_to_nmea_degrees_minutes(decimal_degree):
    degrees = int(abs(decimal_degree))
    minutes_decimal = (abs(decimal_degree) - degrees) * 60
    return "{:02d}{:.4f}".format(degrees, minutes_decimal)


def convert_lon_to_nmea_degrees_minutes(decimal_degree):
    degrees = int(abs(decimal_degree))
    minutes_decimal = (abs(decimal_degree) - degrees) * 60
    return "{:03d}{:.4f}".format(degrees, minutes_decimal)


def get_hemisphere_lat(value):
    return 'N' if value >= 0 else 'S'


def get_hemisphere_lon(value):
    return 'E' if value >= 0 else 'W'


def create_nmea_message(message, checksum_func=compute_nmea_checksum):
    """Create a full NMEA message with checksum."""
    checksum = checksum_func(message)
    return "${}*{}\r\n".format(message, checksum)


def create_way_point_message(latitude_minutes, latitude_hemisphere, longitude_minutes, longitude_hemisphere, number):
    return "OIWPL,{},{},".format(latitude_minutes, latitude_hemisphere) + "{},{},".format(longitude_minutes, longitude_hemisphere) + str(number)


def create_way_point_messages_df(filename, erp_filename):
    """
    Create a DataFrame with waypoint messages from a CSV file.

    :param filename: the name of the CSV file containing waypoint data
    :param erp_filename: the name of the CSV file containing emergency recovery point
    :return: a DataFrame containing NMEA waypoint messages
    """
    try:
        # Load the CSV into a pandas DataFrame
        df = pd.read_csv(filename)
    except Exception as e:
        print(f"Error loading waypoint CSV file: {e}")
        return pd.DataFrame()

    if df.empty:
        print("The waypoints DataFrame is empty.")
        return df

    try:
        # Load the ERP CSV into a pandas DataFrame
        erp_df = pd.read_csv(erp_filename)
        # Only take the first row for the ERP
        erp_df = erp_df.iloc[0:1]
    except Exception as e:
        print(f"Error loading ERP CSV file: {e}")
        return pd.DataFrame()

    # Append ERP to the beginning of the DataFrame
    df = pd.concat([erp_df, df], ignore_index=True)

    # Convert latitude and longitude to desired format
    df['latitude_minutes'] = df['latitude'].apply(
        lambda x: convert_lat_to_nmea_degrees_minutes(float(x)))
    df['longitude_minutes'] = df['longitude'].apply(
        lambda x: convert_lon_to_nmea_degrees_minutes(float(x)))

    # Get hemisphere for latitude and longitude
    df['latitude_hemisphere'] = df['latitude'].apply(get_hemisphere_lat)
    df['longitude_hemisphere'] = df['longitude'].apply(get_hemisphere_lon)

    # Adjust the nmea_waypoints column for the emergency recovery point and the sequential waypoints
    df['nmea_waypoints'] = df.apply(lambda row: create_way_point_message(
        row['latitude_minutes'], row['latitude_hemisphere'], row['longitude_minutes'], row['longitude_hemisphere'],
        row.name), axis=1)

    # Create full NMEA message with checksum
    df['nmea_message'] = df['nmea_waypoints'].apply(
        lambda waypoint: create_nmea_message(waypoint))

    return df


def create_way_point_messages_df_from_list(waypoints, erp):
    """
    Create a DataFrame with waypoint messages from lists of coordinates.

    :param waypoints: a list of tuples with (latitude, longitude)
    :param erp: a tuple with (latitude, longitude) for the emergency recovery point
    :return: a pandas DataFrame containing NMEA waypoint messages
    """
    # Convert the waypoints list and ERP to pandas DataFrames
    waypoints_df = pd.DataFrame(waypoints, columns=['latitude', 'longitude'])
    erp_df = pd.DataFrame([erp], columns=['latitude', 'longitude'])

    # Validate that the DataFrames are not empty
    if waypoints_df.empty:
        print("The waypoints DataFrame is empty.")
        return pd.DataFrame()
    if erp_df.empty:
        print("The ERP DataFrame is empty.")
        return pd.DataFrame()

    # Append ERP to the beginning of the DataFrame
    df = pd.concat([erp_df, waypoints_df], ignore_index=True)

    # Convert latitude and longitude to desired format
    df['latitude_minutes'] = df['latitude'].apply(
        lambda x: convert_lat_to_nmea_degrees_minutes(float(x)))
    df['longitude_minutes'] = df['longitude'].apply(
        lambda x: convert_lon_to_nmea_degrees_minutes(float(x)))

    # Get hemisphere for latitude and longitude
    df['latitude_hemisphere'] = df['latitude'].apply(get_hemisphere_lat)
    df['longitude_hemisphere'] = df['longitude'].apply(get_hemisphere_lon)

    # Adjust the nmea_waypoints column for the emergency recovery point and the sequential waypoints
    df['nmea_waypoints'] = df.apply(lambda row: create_way_point_message(
        row['latitude_minutes'], row['latitude_hemisphere'], row['longitude_minutes'], row['longitude_hemisphere'],
        row.name), axis=1)

    # Create full NMEA message with checksum
    df['nmea_message'] = df['nmea_waypoints'].apply(
        lambda waypoint: create_nmea_message(waypoint))

    return df


def create_waypoint_mission(df, throttle=20, pause_time=0):
    """Generate a waypoint mission from a DataFrame."""

    # Start with the PSEAR command
    psear_cmd = "PSEAR,0,000,{},0,000".format(throttle)
    psear_cmd_with_checksum = "${}*{}\r\n".format(
        psear_cmd, compute_nmea_checksum(psear_cmd))

    # Generate OIWPL commands from the DataFrame
    oi_wpl_cmds = df['nmea_message'].tolist()

    # Concatenate all the commands to form the mission
    mission = psear_cmd_with_checksum + ''.join(oi_wpl_cmds)
    #print(mission)
    return mission


if __name__ == "__main__":
    # filename = "mission1"
    # erp_filename = "erp1"
    # #print("Running tests for helper.py")
    # #print("Open CSV File and create NMEA messages")
    # df = create_way_point_messages_df("in/" + filename + ".csv", "in/" + erp_filename + ".csv")
    # #print(df.to_string())
    # #print("Create waypoint command")
    # mission = create_waypoint_mission(df)
    # #print(mission)
    #
    # # Save mission to file
    # output_file_path = "out/" + filename + ".sea"
    # with open(output_file_path, 'w') as file:
    #     file.write(mission)
    # lat = 25.7581867157068842
    # lon = -80.373954176902771
    # #print("gps converters")
    # #print(convert_lat_to_nmea_degrees_minutes(lat))
    # #print(get_hemisphere_lat(lat))
    # #print(convert_lon_to_nmea_degrees_minutes(lon))
    # #print(get_hemisphere_lon(lon))
    #
    # lat = 25.758402920159952
    # lon = -80.37381336092949
    # #print(convert_lat_to_nmea_degrees_minutes(lat))
    # #print(get_hemisphere_lat(lat))
    # #print(convert_lon_to_nmea_degrees_minutes(lon))
    # #print(get_hemisphere_lon(lon))

        # Example usage:
    message = "OIWPL,2706.85431,N,08016.02364,W,1"
    message = "OIWPL,2545.5030,N,08022.4280,W,1"
    # message = "PSEAC,F,005,000,000,"
    message = "PSEAC,F,000,000,000,"
    message = "PSEAA,-2.2,0.7,222.6,,47.8,-0.04,-0.01,-1.00,-0.01,"
    print("checksum",compute_nmea_checksum(message))  # This should print "7D"

    gga_message = "$GPGGA,115739.00,4158.8441367,N,09147.4416929,W,4,13,0.9,255.747,M,-32.00,M,01,0000*6E\r\n"
    coordinates = get_coordinates(gga_message)
    if coordinates:
        latitude, longitude = coordinates
        #print(f"Latitude: {latitude}")
        #print(f"Longitude: {longitude}")
    else:
        print("Invalid or incomplete GGA sentence")

    messages = [
        "$GPGGA,,,,,,0,,,,M,,M,,*66\r\n",
        "$VCGLL,,,,,,V*04\r\n",
        "$PSEAA,-2.2,0.7,222.6,,47.8,-0.04,-0.01,-1.00,-0.01*7A\r\n",
        "$PSEAB,28.2,49742,0.8,23.9,7858,,,28.3,,0.8,0.0,0.0,,,6*76\r\n",
        "$PSEAD,L,0.0,0.0,0.0,LIDAR_OFF,,1,1*63\r\n",
        "$PSEAE,0.53,11.9,0.76,11.9,,0,0,0,0,0,1,0,1,0,0,1,00000000,0,0,0,,,*68\r\n",
        "$PSEAF,T,2*27\r\n",
        "$PSEAG,M*21\r\n",
        "$PSEAJ,1,0,,,,,,*4C\r\n",
        "$PTQM0,2041,00,00,,00,0.0,,,0,,0.0,,0.0,0.0,,,,0,0*33\r\n",
        "$PTQM1,2041,00,00,,00,0.0,,,0,,0.0,,0.0,0.0,,,,0,0*32\r\n",
        "$DEBUG,,,,,,,,,,,,,,,,,*7D\r\n"
    ]
    message = ''.join(messages)
    gga_message = get_gga(message)

    coordinates = get_coordinates(gga_message)
    #print('teste',coordinates)
    if coordinates:
        latitude, longitude = coordinates
        #print(f"Latitude: {latitude}")
        #print(f"Longitude: {longitude}")
    else:
        print("Invalid or incomplete GGA sentence")

    #print(get_control_mode(message))

    input_tuple = coordinates  # Replace with your tuple of GPS signals
    epsilon = 0.5  # Adjust the value of epsilon as needed

    noisy_tuple = add_laplace_to_tuple(input_tuple, epsilon)
    #print("Noisy Tuple:", noisy_tuple)
    append_tuple_to_csv(input_tuple + noisy_tuple)
    
    #print(get_hemisphere_lat(25))
    #print(get_hemisphere_lon(-80))
    attitude_message = get_attitude_message(message)
    #"PSEAA,-2.2,0.7,222.6,,47.8,-0.04,-0.01,-1.00,-0.01*7A\r\n"
    print(attitude_message)
    print(get_heading(attitude_message))
    

