import arcpy
from arcpy.sa import *
import os

# Path to your Landsat 8 Band 4 (Red) file
band4_path = r"C:\Users\LENOVO\Downloads\B4.TIF"

# Path to your Landsat 8 Band 5 (Near Infrared) file
band5_path = r"C:\Users\LENOVO\Downloads\B5.TIF"

# Path to your Landsat 8 Band 10 (Thermal Infrared) file
band10_path = r"C:\Users\LENOVO\Downloads\B10.TIF"

# Folder where all results will be saved
output_folder = r"C:\LandsatData\LST_Results"

ML = 0.0003342     # RADIANCE_MULT_BAND_10
AL = 0.1           # RADIANCE_ADD_BAND_10

# Landsat 8 Band 10 calibration constants 
K1 = 774.8853
K2 = 1321.0789

# Landsat 8 Band 10 wavelength
LAMBDA = 10.8

def run_lst_workflow():

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    arcpy.env.workspace = output_folder
    arcpy.env.overwriteOutput = True

    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
    else:
        raise RuntimeError("Spatial Analyst license is not available.")

    print("Loading bands...")
    band4 = Raster(band4_path)   # Red
    band5 = Raster(band5_path)   # NIR
    band10 = Raster(band10_path) # Thermal

    # ------------------------------------------------------------------
    # STEP 1: DN -> TOA Spectral Radiance
    #   L = ML * QCAL + AL - 0.29
    # ------------------------------------------------------------------
    print("Step 1/5: Calculating TOA Radiance...")
    toa_radiance = Float(ML) * Float(band10) + Float(AL) - 0.29
    toa_radiance.save(os.path.join(output_folder, "Step1_TOA_Radiance.tif"))

    # ------------------------------------------------------------------
    # STEP 2: TOA Radiance -> Brightness Temperature (Celsius)
    #   BT = (K2 / Ln(K1/L + 1)) - 273.15
    # ------------------------------------------------------------------
    print("Step 2/5: Calculating Brightness Temperature...")
    bt_kelvin_term = Ln((Float(K1) / toa_radiance) + 1)
    brightness_temp_c = (Float(K2) / bt_kelvin_term) - 273.15
    brightness_temp_c.save(os.path.join(output_folder, "Step2_Brightness_Temp_C.tif"))

    brightness_temp_k = brightness_temp_c + 273.15

    # ------------------------------------------------------------------
    # STEP 3: NDVI
    #   NDVI = (NIR - RED) / (NIR + RED)
    # ------------------------------------------------------------------
    print("Step 3/5: Calculating NDVI...")
    ndvi = Float(band5 - band4) / Float(band5 + band4)
    ndvi.save(os.path.join(output_folder, "Step3_NDVI.tif"))

    # ------------------------------------------------------------------
    # STEP 4: Land Surface Emissivity (LSE)
    #   Pv = ((NDVI - NDVImin) / (NDVImax - NDVImin)) ^ 2
    #   E  = 0.004 * Pv + 0.986
    # ------------------------------------------------------------------
    print("Step 4/5: Calculating Land Surface Emissivity...")
    ndvi_min = ndvi.minimum
    ndvi_max = ndvi.maximum
    print("  NDVI min = {:.4f}, NDVI max = {:.4f}".format(ndvi_min, ndvi_max))

    proportion_vegetation = Square((ndvi - ndvi_min) / (ndvi_max - ndvi_min))
    emissivity = 0.004 * proportion_vegetation + 0.986
    emissivity.save(os.path.join(output_folder, "Step4_Emissivity.tif"))

    # ------------------------------------------------------------------
    # STEP 5: Land Surface Temperature (LST)
    #   LST = BT / (1 + (lambda * BT / C2) * ln(E))   [BT in Kelvin]
    #   C2 = 14388 (micrometer-Kelvin)
    #   Final result converted back to Celsius
    # ------------------------------------------------------------------
    print("Step 5/5: Calculating Land Surface Temperature...")
    C2 = 14388.0
    denominator = 1 + ((LAMBDA * brightness_temp_k) / C2) * Ln(emissivity)
    lst_kelvin = brightness_temp_k / denominator
    lst_celsius = lst_kelvin - 273.15
    lst_celsius.save(os.path.join(output_folder, "LST_Celsius.tif"))

    arcpy.CheckInExtension("Spatial")

    print("\nDONE! All 5 steps completed successfully.")
    print("Final Land Surface Temperature map saved to:")
    print("  " + os.path.join(output_folder, "LST_Celsius.tif"))
    print("Intermediate results (radiance, brightness temp, NDVI, emissivity)")
    print("were also saved in the same folder if you want to check them.")

if __name__ == "__main__":
    try:
        run_lst_workflow()
    except Exception as e:
        print("Something went wrong: " + str(e))
        print("Common fixes:")
        print(" - Double check your file paths in USER SETTINGS are correct.")
        print(" - Make sure Band 4, Band 5, and Band 10 all cover the same area.")
        print(" - Make sure the Spatial Analyst extension is licensed in ArcGIS Pro.")
