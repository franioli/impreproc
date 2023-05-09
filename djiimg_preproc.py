from impreproc.djimrk import mrkread, get_images, merge_mrk_exif_data, project_to_utm

if __name__ == "__main__":
    data_dir = "data/matrice/DJI_202303031031_001"
    mkr_file = "data/matrice/DJI_202303031031_001/DJI_202303031031_001_Timestamp.MRK"
    image_ext = "jpg"

    mrk_dict = mrkread(mkr_file)
    exif_dict = get_images(data_dir, image_ext)
    merged_data = merge_mrk_exif_data(mrk_dict, exif_dict)

    if not project_to_utm(
        epsg_from=4326,  # ETRS89
        epsg_to=32632,  # UTM zone 32N
        data_dict=merged_data,
        fields=["lat_mrk", "lon_mrk", "ellh_mrk"],
    ):
        raise RuntimeError("Unable to data project to UTM.")

    # tests for geoid undulation
    from pyproj import CRS, Transformer
    import numpy as np
    import rasterio
    from impreproc.transformations import xy2rc, rc2xy, bilinear_interpolate

    lat, lon, ellh = 45.463873, 9.190653, 100.0
    epsg_from = 4326  # ETRS89
    epsg_to = 32632  # UTM zone 32N

    crs_from = CRS.from_epsg(epsg_from)
    crs_to = CRS.from_epsg(epsg_to)
    transformer = Transformer.from_crs(crs_from=crs_from, crs_to=crs_to)
    x, y, z_ellh = transformer.transform(lat, lon, ellh, direction="FORWARD")

    # Load geoid heights from geotiff
    fname = "data/ITALGEO05_E00.tif"
    with rasterio.open(fname) as src:
        # Convert lat/lon to row/col
        row, col = xy2rc(src.transform, lon, lat)
        # Intepolate geoid height
        geoid_undulation = bilinear_interpolate(src.read(1), col, row)

    assert np.isclose(x, 514904.631, rtol=1e-4)
    assert np.isclose(y, 5034500.589, rtol=1e-4)
    assert np.isclose(z_ellh, 100.0, rtol=1e-5)

    print("Process completed.")
