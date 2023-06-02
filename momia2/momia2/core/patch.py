__author__ = 'jz-rolling'
__version__ = '0.2.1' # revised docstrings using cursor + GPT4

from ..utils import *
from ..segment import *
from ..plot import *
import pandas as pd
from skimage.segmentation import watershed
import PIL,io
from ..classify import run_particle_labeler
from matplotlib import pyplot as plt
from skimage import morphology

__all__ = ['Patch']


class Patch:

    def __init__(self,
                 image_dict=None,
                 configfile=None,
                 image_id=0,
                 ref_channel=-1,
                 store_backup=False):
        # make sure that the number of images match the number of channels provided.
        # modularize Image class
        self.id = image_id
        self.data = {}
        self._data = {}
        self.seed = None
        self.labeled_seeds = None
        self.labeled_mask = None
        self.config = load_config(configfile)
        self.mask = None
        self.prob_mask = None
        self.pixel_microns = 0.065
        self.shape = (2048, 2048)
        self.channels = []
        self.ref_channel = ''
        self.bbox = ()
        self.cache = PatchCache()
        self.store_backup = store_backup
        self.regionprops = pd.DataFrame()
        self.boundaries = None
        self.wd = './'
        if isinstance(image_dict,dict):
            self.load_data(image_dict,
                           ref_channel=ref_channel)

    def load_data(self,image_dict,
                  image_id=0,
                  ref_channel=-1):
        self.id = image_id
        self.data = image_dict
        self.channels = list(image_dict.keys())
        if isinstance(ref_channel, int):
            self.ref_channel = self.channels[ref_channel]
        elif isinstance(ref_channel, str):
            self.ref_channel = ref_channel
        else:
            raise ValueError('reference channel should be integer or string.')
        self.shape = self.data[self.ref_channel].shape
        if self.store_backup:
            self._data = self.data.copy()

    def revert(self):
        if self.store_backup:
            self.data = self._data.copy()
        else:
            print('No raw data found. Set "store_backup" to True to backup raw data.')



    def load_seed(self, seed):
        if seed.shape != self.shape:
            raise ValueError("The shapes of seed image and target images don't match!")
        self.seed = seed

    def load_mask(self, mask):
        if mask.shape != self.shape:
            raise ValueError("The shapes of mask image and target images don't match!")
        self.mask = mask

    def load_labeled_mask(self, labeled_mask):
        if labeled_mask.shape != self.shape:
            raise ValueError("The shapes of labeled mask and target images don't match!")
        self.labeled_mask = labeled_mask

    def preprocess_images(self, func=None, channels = 'all', **kwargs):
        target_channels = []
        if isinstance(channels,str):
            if channels in ['ALL','All','all','-']:
                target_channels=self.channels
            elif channels in ['FL','fl','Fluorescence','fluorescence','F','f']:
                target_channels = [c for c in self.channels if c != self.ref_channel]
            elif channels in ['Ref','ref','Reference','reference','R','r']:
                target_channels = [self.ref_channel]
            elif channels in self.channels:
                target_channels = [channels]
            else:
                raise ValueError('Invalid channel variable "{}".'.format(channels))
        elif isinstance(channels,list):
            for c in channels:
                if c in self.channels:
                    target_channels.append(c)
                else:
                    raise ValueError('Channel "{}" not found.'.format(c))
        try:
            for c in target_channels:
                self.data[c] = func(self.data[c],**kwargs)
        except:
            print('Failed in applying function {} on these channels: {}'.format(func._name_, target_channels))

    def crop_edge(self,edge_fraction=None):
        if isinstance(edge_fraction,float):
            self.config['IMAGE']['EDGE'] = edge_fraction
        else:
            edge_fraction = self.config['IMAGE']['EDGE']
        if 0 <= edge_fraction < 0.4:
            crop_width = int(edge_fraction * self.shape[1])
            crop_height = int(edge_fraction * self.shape[0])
            w1, w2 = crop_width, self.shape[1] - crop_width
            h1, h2 = crop_height, self.shape[0] - crop_height
            self.shape = (h2 - h1, w2 - w1)
        else:
            raise ValueError('Edge fraction should be no higher than 0.4 (40% from each side)!')

        # crope edge
        for channel, data in self.data.items():
            self.data[channel] = self.data[channel][h1:h2, w1:w2]

    def correct_xy_drift(self,
                         reference_channel=None,
                         invert_ref=None,
                         max_drift=None):
        """
        Planar drift correction.
        :param reference_channel: specify reference channel, uses Patch.ref_channel by default.
        :param invert_ref: if invert reference channel data, set to True if reference channel has a light background, e.g. phase contrast.
        :param max_drift: maximum drift (in pixels) to correct for.
        """
        if reference_channel is None:
            reference_channel = self.config['IMAGE']['DRIFT_CORRECTION']['REFERENCE']
            reference_image = self.get_ref_image()
        elif isinstance(reference_channel,str):
            if reference_channel == 'default':
                reference_channel = self.ref_channel
                reference_image = self.get_ref_image()
            elif reference_channel in list(self.data.keys()):
                reference_image = self.data[reference_channel]
                self.config['IMAGE']['DRIFT_CORRECTION']['REFERENCE']=reference_channel
        else:
            raise ValueError('Channel {} not found!'.format(reference_channel))

        if invert_ref is None:
            invert_ref = self.config['IMAGE']['DRIFT_CORRECTION']['INVERT']
        elif isinstance(invert_ref,bool):
            self.config['IMAGE']['DRIFT_CORRECTION']['INVERT']=bool(invert_ref)
        else:
            raise ValueError('The variable "invert_ref" should be boolean, not {}!'.format(type(invert_ref)))

        if max_drift is None:
            max_drift = self.config['IMAGE']['DRIFT_CORRECTION']['MAX_DRIFT_PIX']
        elif isinstance(max_drift,(int,float)):
            self.config['IMAGE']['DRIFT_CORRECTION']['MAX_DRIFT_PIX']=bool(max_drift)
        else:
            raise ValueError('The variable "max_drift" should be float or int, not {}!'.format(type(max_drift)))

        # invert image if necessary
        if invert_ref:
            reference_image = 100 + reference_image.max() - reference_image
        # correct xy drift by phase cross correlation
        for channel, data in self.data.items():
            if channel != reference_channel:
                shift = drift_detection(reference_image,data,upsample_factor=10)
                if max(np.abs(shift)) <= max_drift:
                    offset_image = drift_correction(data, shift)
                    self.data[channel] = offset_image

    def generate_mask(self,
                      method=1,
                      min_particle_size=50,
                      min_hole_size=50,
                      **kwargs):
        mask = BinarizeLegend(method, **kwargs).predict(self.get_ref_image())
        mask = morphology.remove_small_holes(mask,min_hole_size)
        mask = morphology.remove_small_objects(mask,min_particle_size)
        self.mask = mask

    def label_mask(self):
        self.labeled_mask = measure.label(self.mask)

    def locate_particles(self,
                         use_intensity=True,
                         cache_mask = False):
        if self.labeled_mask.max() > 0:
            if use_intensity:
                self.regionprops = get_regionprop(self.labeled_mask, intensity_image=self.get_ref_image())
            else:
                self.regionprops = get_regionprop(self.labeled_mask, intensity_image=None)
            self.regionprops.set_index('$label', inplace=True)
            self.regionprops['$image_id'] = [self.id] * len(self.regionprops)
            self.regionprops[
                ['$opt-x1', '$opt-y1', '$opt-x2', '$opt-y2', '$touching_edge']] = corrections.optimize_bbox_batch(
                                                                                    self.shape, self.regionprops)
            self.regionprops['$include'] = 1
            self.regionprops['$midlines'] = [[]] * len(self.regionprops)
            self.regionprops['$outline'] = [[]] * len(self.regionprops)
            self.regionprops['$refined_outline'] = [[]] * len(self.regionprops)
            masks = []
            for l in self.regionprops.index:
                x1, y1, x2, y2 = self.regionprops.loc[l, ['$opt-x1', '$opt-y1', '$opt-x2', '$opt-y2']]
                masks.append(self.labeled_mask[x1:x2, y1:y2] == l)
            if cache_mask:
                self.regionprops['$mask'] = masks

    def get_particle_data(self,particle_id):
        """
        return particle data by ID
        :param particle_id: user provided unqiue particle ID
        :return: particle data dict
        """
        if len(self.regionprops)==0:
            self.locate_particles()
        if particle_id not in self.regionprops.index:
            raise ValueError('Particle with label {} not found!'.format(particle_id))

        particle_dict = dict(self.regionprops.loc[particle_id])
        x1,y1,x2,y2 = [particle_dict[x] for x in ['$opt-x1', '$opt-y1', '$opt-x2', '$opt-y2']]
        for c in self.channels:
            particle_dict[c] = self.data[c][x1:x2,y1:y2]
        if '$mask' not in particle_dict:
            particle_dict['$mask'] = (self.labeled_mask==particle_id)[x1:x2,y1:y2]
        return particle_dict

    def get_particle_mask(self,particle_id,cropped=True):
        """
        retrieve particle mask, cropped or not
        :param particle_id: user provided unqiue particle ID
        :param cropped: whether to crop the mask by optimized bbox
        :return: particle binary mask, cropped or not
        """
        if len(self.regionprops)==0:
            self.locate_particles()
        if particle_id not in self.regionprops.index:
            raise ValueError('Particle with label {} not found!'.format(particle_id))
        if not cropped:
            return (self.labeled_mask==particle_id)**1
        else:
            x1, y1, x2, y2 = self.regionprops.loc[particle_id,['$opt-x1', '$opt-y1', '$opt-x2', '$opt-y2']].values
            return (self.labeled_mask==particle_id)[x1:x2,y1:y2]

    def filter_particles(self,
                         filter_dict={'area': (50, 5000),
                                      'aspect_ratio': (0.05, 1),
                                      'solidity': (0.4, 1),
                                      'eccentricity': (0.4, 1),
                                      '$outline': 1,
                                      'max_positive_curvature': (0, 60),
                                      'min_negative_curvature': (0, 15)}):
        # remove particles sitting on the edges
        _accept = [self.regionprops['$touching_edge'].values == 0]
        # filter by range
        for k, r in filter_dict.items():
            if '$' in k:
                _accept.append(np.array([self.regionprops[k].values == r]))
            else:
                vmin, vmax = r
                if k in self.regionprops:
                    v = self.regionprops[k].values
                    _accept.append((v > vmin) * (v < vmax))
                else:
                    print('feature ${}$ not found!'.format(k))
        self.regionprops['$include'] = (np.sum(_accept, axis=0) == len(_accept)) * 1

    def _get_intensity_stats(self, channel):
        """
        Add basic intensity features to the regionprop table
        :params channel: specify channel name
        """
        intensity_stats = []
        if channel not in self.channels:
            raise ValueError('Channel {} not found!'.format(channel))

        channel_data = self.get_channel_data(channel)
        for coords in self.regionprops['$coords'].values:
            particle_data = channel_data[coords[:, 0], coords[:, 1]]
            _cols, particle_stat = basic_intensity_features(particle_data)
            intensity_stats.append(particle_stat)
        columns = ['{}_{}'.format(channel, c) for c in _cols]
        self.regionprops[columns] = intensity_stats

    def get_intensity_stats(self):
        """
        get particle intensity stats of all channels
        """
        for c in self.channels:
            self._get_intensity_stats(c)

    def render_image_features(self, model='default', mode='default'):
        if isinstance(model, str):
            if (model == 'default') & (len(self.cache.feature_columns) == 0):
                self._image2pixelfeatures(mode=mode)
        else:
            model.predict(self)
        return None

    def annot2feature(self):
        use_Gaussian = bool(int(self.config['classification_pixel']['use_Gaussian']))
        pixel_feature_selem = generic.config2selem(str(self.config['classification_pixel']['pixel_feature_selem']))
        self.cache.extract_local_features(use_Gaussian=use_Gaussian, selem=pixel_feature_selem)

    def mask2feature(self, ):
        coords = np.where(self.mask > 0)
        self.cache.pixel_data['xcoord'] = coords[0]
        self.cache.pixel_data['ycoord'] = coords[1]
        self.annot2feature()

    def pixel_data(self):
        return self.cache.pixel_data

    def get_ref_image(self):
        return self.data[self.ref_channel]

    def get_channel_data(self, channel):
        if isinstance(channel,str):
            if channel in self.channels:
                return self.data[channel]
            else:
                raise ValueError('Invalid channel name:{}'.format(channel))
        elif isinstance(channel,int):
            if channel<len(self.channels) and channel >=-1:
                return self.data[self.channels[channel]]
            else:
                raise ValueError('Invalid numeric channel index:{}'.format(channel))
        else:
            raise ValueError('Invalid channel format: {}. Can only be a string or integer'.format(type(channel)))

    def find_outline(self,
                     level=0.1,
                     dilation=False,
                     erosion=False,
                     calculate_curvature = True,
                     angularity_window = 15,
                     dark_background=False,
                     sigma=1,
                     approximate=False,
                     tolerance=0.3,
                     interp_distance=1,
                     min_segment_count=3):

        bending_stat = []
        if len(self.regionprops) > 0:
            outline_list = []
            if '$opt-x1' not in self.regionprops:
                self.regionprops[
                    ['$opt-x1', '$opt-y1', '$opt-x2', '$opt-y2', '$touching_edge']] = corrections.optimize_bbox_batch(
                                                                                            self.shape,
                                                                                            self.regionprops)
            for label in self.regionprops.index:
                x1, y1, x2, y2,touching_edge = self.regionprops.loc[label][
                    ['$opt-x1', '$opt-y1', '$opt-x2', '$opt-y2','$touching_edge']].values.astype(int)
                if not touching_edge:
                    mask = (self.labeled_mask[x1:x2, y1:y2] == label).astype(np.int32)
                    data = self.get_ref_image()[x1:x2, y1:y2]
                    outline = find_contour_marching_squares(mask,data,
                                                            level=level,
                                                            dilation=dilation,
                                                            erosion=erosion,
                                                            dark_background=dark_background,
                                                            sigma=sigma,
                                                            approximate=approximate,
                                                            tolerance=tolerance,
                                                            interp_distance=interp_distance,
                                                            min_segment_count=min_segment_count)
                    if calculate_curvature:
                        bending = -bend_angle_closed(outline,window=angularity_window)
                        bending_stat.append([bending.min(),bending.max(),bending.mean(),
                                             np.percentile(bending,25),np.percentile(bending,75)])
                    outline_list.append(outline)
                else:
                    outline_list.append(np.array([]))
                    if calculate_curvature:
                        bending_stat.append([np.nan]*5)
            self.regionprops['$outline'] = outline_list
            if calculate_curvature:
                self.regionprops[['min_negative_curvature',
                                  'max_positive_curvature',
                                  'mean_curvature', 'Q1_curvature', 'Q3_curvature']] = bending_stat

    def plot(self,
             cell_ids=[],
             figsize=(5, 5),
             outline_prop={},
             midline_prop={},
             cell_plot=False,
             channel=-1):
        print('Rendering cell plot(s)...')
        plot_cells(self,cell_ids,figsize,outline_prop,midline_prop,cell_plot,channel)

    def _image2pixelfeatures(self, mode='default'):
        if mode == 'default':
            sigmas = (0.5, 1.5, 5)
            use_RoG = True
            use_Ridge = True
            use_Sobel = False
            use_Gaussian = True
            use_Shapeindex = True
            num_workers = 12
        elif mode == 'use_config':
            # adopt parameters from configurations
            sigmas = np.array(self.config['classification_pixel']['sigmas'].split(',')).astype(float)
            use_RoG = bool(int(self.config['classification_pixel']['use_RoG']))
            use_Ridge = bool(int(self.config['classification_pixel']['use_Ridge']))
            use_Sobel = bool(int(self.config['classification_pixel']['use_Sobel']))
            use_Gaussian = bool(int(self.config['classification_pixel']['use_Gaussian']))
            use_Shapeindex = bool(int(self.config['classification_pixel']['use_Shapeindex']))
            num_workers = int(self.config['classification_pixel']['num_workers'])
        elif mode == 'fast':
            sigmas = (float(self.config['classification_pixel']['ridge_sigma']))
            use_RoG = True
            use_Ridge = True
            use_Sobel = False
            use_Gaussian = False
            use_Shapeindex = True
            num_workers = 12
        else:
            raise ValueError(
                'Illegal pixel feature extraction mode "{}", use "default", "fast", "use_config" instead.'.format(mode))
        # feature images
        self.cache.prepare_feature_images(self.get_ref_image(),
                                          num_workers=num_workers,
                                          sigmas=sigmas,
                                          rog=use_RoG,
                                          ridge=use_Ridge,
                                          sobel=use_Sobel,
                                          shapeindex=use_Shapeindex)

    def _seed2annot(self):
        from skimage.segmentation import watershed
        from skimage.measure import regionprops_table, label

        # label_seed
        self.labeled_seeds = label(self.seed)

        # adopt parameters from configurations
        ridge_sigma = float(self.config['classification_pixel']['ridge_sigma'])
        min_seed_fraction = float(self.config['classification_pixel']['min_seed_fraction'])
        erosion_selem = generic.config2selem(str(self.config['classification_pixel']['seeded_mask_erosion_selem']))
        dilation_selem = generic.config2selem(str(self.config['classification_pixel']['seeded_mask_dilation_selem']))

        # watershed segment
        ridge = filters.sato(self.get_ref_image(),
                             sigmas=(ridge_sigma),
                             black_ridges=False)
        labeled_mask = watershed(ridge, markers=self.labeled_seeds,
                                 mask=self.mask,
                                 watershed_line=True,
                                 compactness=1)
        rp = pd.DataFrame(regionprops_table(labeled_mask,
                                            intensity_image=(self.seed > 0) * 1,
                                            properties=['coords', 'mean_intensity']))
        if rp['mean_intensity'].max() < min_seed_fraction:
            x, y = np.vstack(rp[rp['mean_intensity'] < min_seed_fraction]['coords'].values).T
            labeled_mask[x, y] = 0
        self.labeled_mask = labeled_mask

        # extract relavent pixel coordinates
        seeded_mask = (labeled_mask > 0) * 1
        core = morphology.binary_erosion(seeded_mask, erosion_selem) * 1
        dilated = morphology.binary_dilation(seeded_mask, dilation_selem) * 1
        residual = ((self.mask - dilated) == 1) * 1
        edge = dilated - core

        # mask to coords
        core_coords = np.array(np.where(core > 0))
        edge_coords = np.array(np.where(edge > 0))
        residual_coords = np.array(np.where(residual > 0))

        # concat coords and annotations
        coords = np.hstack([core_coords, edge_coords, residual_coords])
        annot = [2] * len(core_coords[0]) + \
                [1] * len(edge_coords[0]) + \
                [0] * len(residual_coords[0])
        self.mask = np.zeros(self.mask.shape)
        self.mask[edge == 1] = 1
        self.mask[core == 1] = 2

        self.cache.pixel_data['xcoord'] = coords[0]
        self.cache.pixel_data['ycoord'] = coords[1]
        self.cache.pixel_data['annotation'] = annot

    def annotate_particles(self,
                           percentile_norm_params=(0, 100, 2000, 10000),
                           show_outline=False,
                           outline_color='r',
                           classes={1: 'single cell', 2: 'microcolony', 3: 'others'},
                           saturation=0.85):
        norm = (generic.percentile_normalize(self.get_ref_image(),
                                             percentile_norm_params[0],
                                             percentile_norm_params[1],
                                             percentile_norm_params[2],
                                             percentile_norm_params[3]) * int(saturation * 255)).astype(np.uint8)
        thumbnails = []
        if '$annotation' in self.regionprops.columns:
            annotation = self.regionprops['$annotation'].values
        else:
            annotation = np.zeros(len(self.regionprops))
        for (x0, y0, x1, y1, c) in self.regionprops[['$opt-x1', '$opt-y1', '$opt-x2', '$opt-y2', '$outline']].values:
            if show_outline:
                fig = plt.figure(figsize=(4, 4))
                plt.imshow(self.get_ref_image()[x0:x1, y0:y1], cmap='gist_gray')
                plt.plot(c[0][:, 1], c[0][:, 0], color=outline_color, lw=0.8)
                plt.axis('off')
                img_buf = io.BytesIO()
                plt.savefig(img_buf, bbox_inches='tight')
                thumbnails.append(PIL.Image.open(img_buf))
                plt.close()
            else:
                thumbnails.append(PIL.Image.fromarray(norm[x0:x1, y0:y1]))
        run_particle_labeler(thumbnails, label_dict=classes, annot=annotation)
        self.regionprops['$annotation'] = annotation

    def generate_multi_mask(self, model='default',
                              method=1,
                              channels=[], **kwargs):
        if len(channels) > len(self.channels):
            raise ValueError('Patch image had {} channels but {} channels were provided'.format(len(self.channels),
                                                                                                len(channels)))
        if len(channels) == 0:
            input_images = [self.get_ref_image()]

        elif len(channels) >= 1:
            stack = []
            for c in channels:
                if c in self.data:
                    stack.append(self.data[c])
                else:
                    raise ValueError('Patch image does not have channel "{}".'.format(c))
            input_images = [np.array(stack)]

        if isinstance(model, str):
            if model == 'default':
                model = BinarizeLegend(method=method, config=self.config)
            else:
                raise ModuleNotFoundError('Mask method {} not found!'.format(model))
        mask = MakeMask(model, **kwargs).predict(input_images)[0]
        self.mask = mask


class PatchCache:

    def __init__(self):
        self.gaussians = {}
        self.feature_images = {}
        self.feature_columns = []
        self.pixel_data = pd.DataFrame()

    def prepare_feature_images(self, img, **kwargs):
        self.gaussians, self.feature_images = multiscale_image_feature(img, **kwargs)

    def extract_local_features(self, use_Gaussian=True, **kwargs):
        if len(self.pixel_data) == 0:
            raise ValueError('Pixel coordinates not defined!')
        xcoord, ycoord = self.pixel_data[['xcoord', 'ycoord']].values.T
        feature_images = self.feature_images
        if use_Gaussian:
            for k, g in self.gaussians.items():
                feature_images['Gaussian_{}'.format(k)] = g
        local_pixel_features = local_stat(feature_images, xcoord, ycoord, **kwargs)
        self.feature_columns = local_pixel_features.columns
        self.pixel_data[self.feature_columns] = local_pixel_features.values

def get_regionprop(labeled_image, intensity_image=None):
    regionprop_properties = ['label','bbox','coords','centroid',
                             'area','convex_area','filled_area',
                             'eccentricity','solidity',
                             'major_axis_length','minor_axis_length',
                             'perimeter','equivalent_diameter',
                             'extent','orientation',
                             'inertia_tensor','moments_hu','weighted_moments_hu',
                             'mean_intensity','max_intensity','min_intensity']

    if intensity_image is not None:
        rp_table = pd.DataFrame(measure.regionprops_table(labeled_image,
                                                          intensity_image,
                                                          properties=regionprop_properties))
    else:
        rp_table = pd.DataFrame(measure.regionprops_table(labeled_image,
                                                          intensity_image=(labeled_image>0)*1,
                                                          properties=regionprop_properties))
    areas = rp_table['area'].values
    perimeter = rp_table['perimeter'].values
    rp_table['compactness'] = (perimeter**2)/(4*np.pi*areas)
    rp_table['rough_length'] = (perimeter-np.sqrt(perimeter**2-16*areas))/4
    rp_table['aspect_ratio'] = np.round(rp_table['minor_axis_length'].values/rp_table['major_axis_length'].values,3)
    rp_table.rename(columns={'bbox-0':'$bbox-0',
                             'bbox-1':'$bbox-1',
                             'bbox-2':'$bbox-2',
                             'bbox-3':'$bbox-3',
                             'coords':'$coords',
                             'label':'$label',
                             'centroid-0':'$centroid-0',
                             'centroid-1':'$centroid-1'},
                    inplace=True)
    return rp_table

    """
    def load_config(self, config):
        if 'ConfigParser' in str(type(config)):
            self.config = config
        else:
            self.config = Config(config).config
    """



