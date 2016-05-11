
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import copy
import numpy as np

import astropy.io.fits as pyfits
import astropy.wcs as pywcs
from astropy import units as u
from astropy.coordinates import SkyCoord

import fermipy.utils as utils

class WCSProj(object):
    """Class that encapsulates both a WCS object and the definition of
    the image extent (number of pixels).  Also provides a number of
    helper methods for accessing the properties of the WCS object."""
    def __init__(self,wcs,npix):

        self._wcs = wcs
        self._npix = npix

    @property
    def wcs(self):
        return self._wcs

    @property
    def npix(self):
        return self._npix

    @staticmethod
    def create(skydir,cdelt,npix,coordsys='CEL',projection='AIT'):
        crpix = npix/2.+0.5
        wcs = create_wcs(skydir,coordsys,projection,
                         cdelt,crpix)
        return WCSProj(wcs,npix)

    
def create_wcs(skydir, coordsys='CEL', projection='AIT',
               cdelt=1.0, crpix=1., naxis=2, energies=None):
    """Create a WCS object.

    Parameters
    ----------

    skydir : `~astropy.coordinates.SkyCoord`
        Sky coordinate of the WCS reference point.

    coordsys : str

    projection : str

    cdelt : float

    crpix : float
        

    """

    w = pywcs.WCS(naxis=naxis)

    if coordsys == 'CEL':
        w.wcs.ctype[0] = 'RA---%s' % (projection)
        w.wcs.ctype[1] = 'DEC--%s' % (projection)
        w.wcs.crval[0] = skydir.icrs.ra.deg
        w.wcs.crval[1] = skydir.icrs.dec.deg
    elif coordsys == 'GAL':
        w.wcs.ctype[0] = 'GLON-%s' % (projection)
        w.wcs.ctype[1] = 'GLAT-%s' % (projection)
        w.wcs.crval[0] = skydir.galactic.l.deg
        w.wcs.crval[1] = skydir.galactic.b.deg
    else:
        raise Exception('Unrecognized coordinate system.')

    w.wcs.crpix[0] = crpix
    w.wcs.crpix[1] = crpix
    w.wcs.cdelt[0] = -cdelt
    w.wcs.cdelt[1] = cdelt

    w = pywcs.WCS(w.to_header())
    if naxis == 3 and energies is not None:
        w.wcs.crpix[2] = 1
        w.wcs.crval[2] = 10 ** energies[0]
        w.wcs.cdelt[2] = 10 ** energies[1] - 10 ** energies[0]
        w.wcs.ctype[2] = 'Energy'

    return w


def offset_to_sky(skydir, offset_lon, offset_lat,
                  coordsys='CEL', projection='AIT'):
    """Convert a cartesian offset (X,Y) in the given projection into
    a spherical coordinate."""

    offset_lon = np.array(offset_lon, ndmin=1)
    offset_lat = np.array(offset_lat, ndmin=1)

    w = create_wcs(skydir, coordsys, projection)
    pixcrd = np.vstack((offset_lon, offset_lat)).T

    return w.wcs_pix2world(pixcrd, 0)


def offset_to_skydir(skydir, offset_lon, offset_lat,
                     coordsys='CEL', projection='AIT'):
    """Convert a cartesian offset (X,Y) in the given projection into
    a spherical coordinate."""

    offset_lon = np.array(offset_lon, ndmin=1)
    offset_lat = np.array(offset_lat, ndmin=1)

    w = create_wcs(skydir, coordsys, projection)
    return SkyCoord.from_pixel(offset_lon, offset_lat, w, 0)


def sky_to_offset(skydir, lon, lat, coordsys='CEL', projection='AIT'):
    """Convert sky coordinates to a projected offset.  This function
    is the inverse of offset_to_sky."""
    
    w = create_wcs(skydir, coordsys, projection)
    skycrd = np.vstack((lon, lat)).T
    
    if len(skycrd) == 0:
        return skycrd
    
    return w.wcs_world2pix(skycrd, 0)


def skydir_to_pix(skydir, wcs):
    """Convert skydir object to pixel coordinates."""

    if 'RA' in wcs.wcs.ctype[0]:
        xpix, ypix = wcs.wcs_world2pix(skydir.ra.deg, skydir.dec.deg, 0)
    elif 'GLON' in wcs.wcs.ctype[0]:
        xpix, ypix = wcs.wcs_world2pix(skydir.galactic.l.deg,
                                       skydir.galactic.b.deg, 0)
    else:
        raise Exception('Unrecognized WCS coordinate system.')

    return [xpix, ypix]


def pix_to_skydir(xpix, ypix, wcs):
    """Convert pixel coordinates to a skydir object."""

    if 'RA' in wcs.wcs.ctype[0]:
        ra, dec = wcs.wcs_pix2world(xpix, ypix, 0)
        return SkyCoord(ra, dec, unit=u.deg)
    elif 'GLON' in wcs.wcs.ctype[0]:
        glon, glat = wcs.wcs_pix2world(xpix, ypix, 0)
        return SkyCoord(glon, glat, unit=u.deg,
                        frame='galactic').transform_to('icrs')
    else:
        raise Exception('Unrecognized WCS coordinate system.')


def get_coordsys(wcs):
    if 'RA' in wcs.wcs.ctype[0]:
        return 'CEL'
    elif 'GLON' in wcs.wcs.ctype[0]:
        return 'GAL'
    else:
        raise Exception('Unrecognized WCS coordinate system.')


def get_projection(wcs):

    if 'RA' in wcs.wcs.ctype[0]:
        return 'CEL'
    elif 'GLON' in wcs.wcs.ctype[0]:
        return 'GAL'
    else:
        raise Exception('Unrecognized WCS coordinate system.')

    
def get_target_skydir(config,ref_skydir=None):

    if ref_skydir is None:
        ref_skydir = SkyCoord(0.0,0.0,unit=u.deg)
    
    radec = config.get('radec', None)

    if isinstance(radec, str):
        return SkyCoord(radec, unit=u.deg)
    elif isinstance(radec, list):
        return SkyCoord(radec[0], radec[1], unit=u.deg)

    ra = config.get('ra', None)
    dec = config.get('dec', None)

    if ra is not None and dec is not None:
        return SkyCoord(ra, dec, unit=u.deg)

    glon = config.get('glon', None)
    glat = config.get('glat', None)

    if glon is not None and glat is not None:
        return SkyCoord(glon, glat, unit=u.deg,
                        frame='galactic').transform_to('icrs')

    offset_ra = config.get('offset_ra', None)
    offset_dec = config.get('offset_dec', None)
    
    if offset_ra is not None and offset_dec is not None:
        return offset_to_skydir(ref_skydir, offset_ra, offset_dec,
                                coordsys='CEL')[0]

    offset_glon = config.get('offset_glon', None)
    offset_glat = config.get('offset_glat', None)
    
    if offset_glon is not None and offset_glat is not None:
        return offset_to_skydir(ref_skydir, offset_glon, offset_glat,
                                coordsys='GAL')[0]
        
    return ref_skydir


def wcs_to_axes(w, npix):
    """Generate a sequence of bin edge vectors corresponding to the
    axes of a WCS object."""

    npix = npix[::-1]

    x = np.linspace(-(npix[0]) / 2., (npix[0]) / 2.,
                    npix[0] + 1) * np.abs(w.wcs.cdelt[0])
    y = np.linspace(-(npix[1]) / 2., (npix[1]) / 2.,
                    npix[1] + 1) * np.abs(w.wcs.cdelt[1])

    cdelt2 = np.log10((w.wcs.cdelt[2] + w.wcs.crval[2]) / w.wcs.crval[2])

    z = (np.linspace(0, npix[2], npix[2] + 1)) * cdelt2
    z += np.log10(w.wcs.crval[2])

    return x, y, z


def wcs_to_coords(w, shape):
    """Generate an N x D list of pixel center coordinates where N is
    the number of pixels and D is the dimensionality of the map."""
    if w.naxis == 2:
        y, x = wcs_to_axes(w,shape)
    elif w.naxis == 3:
        z, y, x = wcs_to_axes(w,shape)
    else:
        raise Exception("Wrong number of WCS axes %i"%w.naxis)
    
    x = 0.5*(x[1:] + x[:-1])
    y = 0.5*(y[1:] + y[:-1])

    if w.naxis == 2:
        x = np.ravel(np.ones(shape)*x[:,np.newaxis])
        y = np.ravel(np.ones(shape)*y[np.newaxis,:])
        return np.vstack((x,y))    

    z = 0.5*(z[1:] + z[:-1])    
    x = np.ravel(np.ones(shape)*x[:,np.newaxis,np.newaxis])
    y = np.ravel(np.ones(shape)*y[np.newaxis,:,np.newaxis])       
    z = np.ravel(np.ones(shape)*z[np.newaxis,np.newaxis,:])
         
    return np.vstack((x,y,z))    


def wcs_to_skydir(wcs):

    lon = wcs.wcs.crval[0]
    lat = wcs.wcs.crval[1]

    coordsys = get_coordsys(wcs)

    if coordsys == 'GAL':
        return SkyCoord(lon,lat,unit='deg',frame='galactic').transform_to('icrs')
    else:
        return SkyCoord(lon,lat,unit='deg',frame='icrs')


def is_galactic(wcs):

    coordsys = get_coordsys(wcs)
    if coordsys == 'GAL':
        return True
    elif coordsys == 'CEL':
        return False
    else:
        raise Exception('Unsupported coordinate system: %s'%coordsys)