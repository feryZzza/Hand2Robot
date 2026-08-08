uint8 HANDEDNESS_UNKNOWN=0
uint8 HANDEDNESS_LEFT=1
uint8 HANDEDNESS_RIGHT=2

std_msgs/Header header
string schema_version
uint32 sequence
uint8 handedness
string source
geometry_msgs/Point[21] joints_2d_px
geometry_msgs/Point[21] joints_3d_m
bool[21] joints_3d_valid
float32[21] confidence
bool valid
