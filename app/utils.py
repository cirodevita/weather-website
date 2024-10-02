
def convert_f_to_c(temp_in_fahrenheit):
    convert = (temp_in_fahrenheit - 32) * 5 / 9
    return float("{:.2f}".format(convert))