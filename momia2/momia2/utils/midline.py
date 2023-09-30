__author__ = 'jz-rolling'
__version__ = '0.2.1' # revised docstrings using cursor + GPT4

from .contour import *
import warnings


def midline_approximation(skeleton,
                          smoothed_contour,
                          move_pole1=False,
                          move_pole2=False,
                          anchor_length=3,
                          tolerance=0.1, max_iteration=10):
    """
    Approximation of a smooth midline with skeleton and a smoothed contour.

    :param skeleton: A numpy array of shape (n, 2) representing the skeleton of a 2D object.
    :param smoothed_contour: A numpy array of shape (m, 2) representing the smoothed contour of a 2D object.
    :param tolerance: A float representing the maximum distance between the midline and the skeleton at which convergence is achieved.
    :param max_iteration: An integer representing the maximum number of iterations to perform.
    :return: A tuple containing a numpy array of shape (p, 2) representing the midline approximation and a boolean indicating whether convergence was achieved.
    """
    midline = skeleton.copy()
    pole1_anchor = []
    pole2_anchor = []

    if not move_pole1:
        pole1_anchor = midline[:anchor_length]
        midline = midline[anchor_length:]
    if not move_pole2:
        pole2_anchor = midline[-anchor_length:]
        midline = midline[:-anchor_length]

    n = 0
    converged = False
    while n < max_iteration:
        updated_midline = skeleton_contour_intersect_points(midline, smoothed_contour)
        dxy = updated_midline - midline
        midline = spline_approximation(updated_midline,
                                               n=len(updated_midline),
                                               smooth_factor=1,
                                       closed=False)
        if np.abs(dxy).mean() <= tolerance:
            converged = True
            break
        n += 1
    stiched_midline = []
    if not move_pole1:
        stiched_midline.append(pole1_anchor)
    stiched_midline.append(updated_midline)
    if not move_pole2:
        stiched_midline.append(pole2_anchor)
    midline = np.vstack(stiched_midline)
    return midline.astype(float), converged


def skeleton_analysis(mask,
                      pruning=False,
                      min_branch_length=5,
                      max_iterations=30,
                      method='zhang'):
    """
    find all skeleton branch(es) from a binary mask and sort the pixel coordinates accordingly
    :param mask:
    :param pruning:
    :param min_branch_length:
    :param max_iterations:
    :param method:
    :return:
    """
    warnings.filterwarnings("ignore")
    skeleton = morphology.skeletonize(mask,method=method)*2
    endpoints, branch_points, skeleton = locate_nodes(skeleton)
    anchor_points = endpoints+branch_points
    skeleton_branches = []
    n = 0
    if (len(endpoints) >= 2): #and (len(branch_points) <= 10):
        while True:
            if len(anchor_points) == 0:
                break
            if n>=max_iterations:
                break
            is_real_pole = [0,0]
            startpoint = anchor_points[0]
            if startpoint in endpoints:
                is_real_pole[0] = 1
            xcoords,ycoords = neighbor_search(skeleton,startpoint)
            anchor_points.remove(startpoint)
            if len(xcoords)>=1:
                lx,ly = xcoords[-1],ycoords[-1]
                node_count, node_coords = cubecount_with_return(skeleton, lx, ly, 3)
                if (node_count == 0) and ([lx,ly] in endpoints):
                    is_real_pole[1] = 1
                    anchor_points.remove([lx, ly])
                elif (node_count == 1):
                    lx, ly = node_coords[0]
                    if [lx, ly] in anchor_points:
                        anchor_points.remove([lx, ly])
                    xcoords.append(lx)
                    ycoords.append(ly)
                else:
                    for xy in node_coords:
                        if distance([lx,ly],xy) == 1:
                            lx,ly = xy
                            break
                    if [lx, ly] in anchor_points:
                        anchor_points.remove([lx, ly])
                    xcoords.append(lx)
                    ycoords.append(ly)
                skeleton_branches.append([is_real_pole, xcoords, ycoords])
            n+=1
        branch_copy = skeleton_branches.copy()
        if pruning:
            for branch in branch_copy:
                if len(branch[1]) <= min_branch_length:
                    skeleton_branches.remove(branch)
            if len(skeleton_branches)==1:
                skeleton_branches[0][0]=[1,1]
        if n < max_iterations:
            return skeleton_branches, skeleton
        else:

            return [], skeleton
    else:
        print('hi')
        return [], skeleton

def locate_nodes(skeleton):
    """
    traverse the skeleton points and locate branch and terminal pixels.
    :param skeleton: binary skeleton generated by calling skimage.morphology.skeletonize
    :return: a list of three short lists of coordinates:
             @endpoints: outreaching pole coordinates, there should be one for each branch
             @branch_points: branching point coordinates, there should be one for each branch
             @skeleton: labeled skeleton
    """
    warnings.filterwarnings("ignore")
    endpoints = []
    branch_points = []
    skeleton_path = np.where(skeleton > 0)
    skeleton_length = len(skeleton_path[0])
    if skeleton_length > 5:
        for i in range(skeleton_length):
            x = skeleton_path[0][i]
            y = skeleton_path[1][i]
            if cube_nonzero(skeleton, x, y) == 1:
                endpoints.append([x, y])
            if cube_nonzero(skeleton, x, y) == 2:
                _n, _neighbors = cube_nonzero_with_return(skeleton, x, y)
                _x0, _y0 = _neighbors[0]
                _x1, _y1 = _neighbors[1]
                dist = abs(_x0 - _x1) + abs(_y0 - _y1)
                if dist == 1:
                    skeleton[x, y] = 0
                    if skeleton[_x0, _y0] == 3:
                        skeleton[_x0, _y0] = 2
                    if skeleton[_x1, _y1] == 3:
                        skeleton[_x1, _y1] = 2
                    if [_x0, _y0] in branch_points:
                        branch_points.remove([_x0, _y0])
                    if [_x1, _y1] in branch_points:
                        branch_points.remove([_x1, _y1])
            if cube_nonzero(skeleton, x, y) > 2:
                branch_points.append([x, y])
                skeleton[x, y] = 3
        return endpoints, branch_points, skeleton
    else:
        return endpoints, branch_points, skeleton


def merge_branch_points(skeleton_coords,
                        max_dist=3):
    centroid_groups_id = []
    centroid_groups_x = []
    centroid_groups_y = []
    centroid_groups = []

    for p,x,y in skeleton_coords:
        if p[0]==0:
            centroid_groups_x.append(x[0])
            centroid_groups_y.append(y[0])
        if p[1]==0:
            centroid_groups_x.append(x[-1])
            centroid_groups_y.append(y[-1])
    centroid_groups_x=np.array(centroid_groups_x)
    centroid_groups_y=np.array(centroid_groups_y)
    new_coords = []
    for p,x,y in skeleton_coords:
        new_x = x.copy()
        new_y = y.copy()
        if p[0]==0:
            new_x[0]=centroid_groups_x[np.abs(centroid_groups_x-x[0])<max_dist].mean()
            new_y[0]=centroid_groups_y[np.abs(centroid_groups_y-y[0])<max_dist].mean()
        if p[1]==0:
            new_x[-1]=centroid_groups_x[np.abs(centroid_groups_x-x[-1])<max_dist].mean()
            new_y[-1]=centroid_groups_y[np.abs(centroid_groups_y-y[-1])<max_dist].mean()
        new_coords.append([p,new_x,new_y])
    return new_coords

@jit(nopython=True, cache=True)
def neighbor_search(input_map, endpoint, max_iterations=500):
    output_x = []
    output_y = []
    end_reached = False
    x, y = endpoint[0], endpoint[1]
    counter = 0
    while not end_reached:
        if counter >= max_iterations:
            break
        n_neighbor, neighbor_list = cubecount_with_return(input_map, x, y, 2)
        if n_neighbor == 0:
            input_map[x, y] = 1
            output_x.append(x)
            output_y.append(y)
            end_reached = True
        elif n_neighbor == 1:
            input_map[x, y] = 1
            output_x.append(x)
            output_y.append(y)
            x, y = neighbor_list[-1]
        elif n_neighbor >= 2:
            input_map[x, y] = 1
            output_x.append(x)
            output_y.append(y)
            end_reached = True
        counter += 1
    return output_x, output_y


@jit(nopython=True, cache=True)
def cubesum(mask, px, py, val):
    n = 0
    for i in [0, 1, 2, 3, 5, 6, 7, 8]:
        dx = int(i / 3)
        dy = i - dx * 3
        x1, y1 = px + dx - 1, py + dy - 1
        if mask[x1, y1] == val:
            n += 1
    return n


@jit(nopython=True, cache=True)
def cube_nonzero(mask, px, py):
    n = 0
    for i in [0, 1, 2, 3, 5, 6, 7, 8]:
        dx = int(i / 3)
        dy = i - dx * 3
        x1, y1 = px + dx - 1, py + dy - 1
        if mask[x1, y1] > 0:
            n += 1
    return n


@jit(nopython=True, cache=True)
def cube_nonzero_with_return(mask, px, py):
    retlist = []
    n = 0
    for i in [0, 1, 2, 3, 5, 6, 7, 8]:
        dx = int(i / 3)
        dy = i - dx * 3
        x1, y1 = px + dx - 1, py + dy - 1
        if mask[x1, y1] > 0:
            retlist.append([x1, y1])
            n += 1
    return n, retlist


@jit(nopython=True, cache=True)
def cubecount_with_return(mask, px, py, val):
    retlist = []
    n = 0
    for i in [0, 1, 2, 3, 5, 6, 7, 8]:
        dx = int(i / 3)
        dy = i - dx * 3
        x1, y1 = px + dx - 1, py + dy - 1
        if mask[x1, y1] == val:
            retlist.append([x1, y1])
            n += 1
    return n, retlist


def find_poles(smoothed_skeleton,
               smoothed_contour,
               find_pole1=True,
               find_pole2=True,
               gap=4, ):
    """

    :param smoothed_skeleton:
    :param smoothed_contour:
    :param find_pole1:
    :param find_pole2:
    :param gap:
    :return:
    """
    # find endpoints and their nearest neighbors on a midline
    length = len(smoothed_skeleton)
    extended_pole1 = [smoothed_skeleton[0]]
    extended_pole2 = [smoothed_skeleton[-1]]
    i = 0
    j = 0
    if find_pole1:
        for i in range(5):
            p1 = smoothed_skeleton[i]
            p2 = smoothed_skeleton[i + gap]
            # find the two intersection points between
            # the vectorized contour and line through pole1
            intersection_points_pole1 = line_contour_intersection(p1, p2, smoothed_contour)
            # find the interesection point with the same direction as the outward pole vector
            dxy_1 = p1 - p2
            p1_tile = np.tile(p1, (len(intersection_points_pole1), 1))
            p1dot = (intersection_points_pole1 - p1_tile) * dxy_1
            index_1 = np.where((p1dot[:, 0] > 0) & (p1dot[:, 1] > 0))[0]
            if len(index_1) > 0:
                extended_pole1 = intersection_points_pole1[index_1]
                break
    else:
        i = 1

    if find_pole2:
        for j in range(5):
            p3 = smoothed_skeleton[-1 - j]
            p4 = smoothed_skeleton[-1 - gap - j]
            # find the two intersection points between
            # the vectorized contour and line through pole1
            intersection_points_pole2 = line_contour_intersection(p3, p4, smoothed_contour)
            # find the interesection point with the same direction as the outward pole vector
            dxy_2 = p3 - p4
            p3_tile = np.tile(p3, (len(intersection_points_pole2), 1))
            p3dot = (intersection_points_pole2 - p3_tile) * dxy_2
            index_2 = np.where((p3dot[:, 0] > 0) & (p3dot[:, 1] > 0))[0]
            if len(index_2) > 0:
                extended_pole2 = intersection_points_pole2[index_2]
                break
    else:
        j = 1
    trimmed_midline = smoothed_skeleton[i:length - j]
    return extended_pole1, extended_pole2, trimmed_midline


def find_poles_simp(smoothed_skeleton,
                    smoothed_contour,
                    find_pole1=True,
                    find_pole2=True,
                    gap=3):
    """
    find endpoints and their nearest neighbors on a midline
    :param smoothed_skeleton:
    :param smoothed_contour:
    :param find_pole1:
    :param find_pole2:
    :param gap:
    :return:
    """

    length = len(smoothed_skeleton)
    extended_pole1 = [smoothed_skeleton[0]]
    extended_pole2 = [smoothed_skeleton[-1]]
    i = 0
    j = 0
    if find_pole1:
        for i in range(5):
            p1 = smoothed_skeleton[i]
            p2 = smoothed_skeleton[i + gap]
            # find the two intersection points between
            # the vectorized contour and line through pole1
            intersection_points_pole1 = line_contour_intersection(p1, p2, smoothed_contour)
            # find the interesection point with the same direction as the outward pole vector
            dxy_1 = p1 - p2
            p1_tile = np.tile(p1, (len(intersection_points_pole1), 1))
            p1dot = (intersection_points_pole1 - p1_tile) * dxy_1
            index_1 = np.where((p1dot[:, 0] > 0) & (p1dot[:, 1] > 0))[0]
            if len(index_1) > 0:
                extended_pole1 = intersection_points_pole1[index_1]
                break
    else:
        i = 1

    if find_pole2:
        for j in range(5):
            p3 = smoothed_skeleton[-1 - j]
            p4 = smoothed_skeleton[-1 - gap - j]
            # find the two intersection points between
            # the vectorized contour and line through pole1
            intersection_points_pole2 = line_contour_intersection(p3, p4, smoothed_contour)
            # find the interesection point with the same direction as the outward pole vector
            dxy_2 = p3 - p4
            p3_tile = np.tile(p3, (len(intersection_points_pole2), 1))
            p3dot = (intersection_points_pole2 - p3_tile) * dxy_2
            index_2 = np.where((p3dot[:, 0] > 0) & (p3dot[:, 1] > 0))[0]
            if len(index_2) > 0:
                extended_pole2 = intersection_points_pole2[index_2]
                break
    else:
        j = 1
    trimmed_midline = smoothed_skeleton[i:length - j]
    return extended_pole1, extended_pole2, trimmed_midline


def extend_skeleton(smoothed_skeleton,
                    smoothed_contour,
                    find_pole1=True,
                    find_pole2=True,
                    subdivide_pole_segment=5,
                    interpolation_factor=1):
    # initiate approximated tip points
    new_pole1, new_pole2, smoothed_skeleton = find_poles(smoothed_skeleton,
                                                         smoothed_contour,
                                                         find_pole1=find_pole1,
                                                         find_pole2=find_pole2)

    extended_skeleton = []
    if find_pole1:
        segment1 = (np.array([np.linspace(new_pole1[0][0], smoothed_skeleton[0, 0], subdivide_pole_segment),
                              np.linspace(new_pole1[0][1], smoothed_skeleton[0, 1], subdivide_pole_segment)]).T)[:-1]
    else:
        segment1 = new_pole1
    if find_pole2:
        segment2 = (np.array([np.linspace(smoothed_skeleton[-1, 0], new_pole2[0][0], subdivide_pole_segment),
                              np.linspace(smoothed_skeleton[-1, 1], new_pole2[0][1], subdivide_pole_segment)]).T)[1:]
    else:
        segment2 = new_pole2

    extended_skeleton = np.concatenate([segment1,
                                        smoothed_skeleton,
                                        segment2])
    return spline_approximation(extended_skeleton,
                                n=int(interpolation_factor * len(smoothed_skeleton)),
                                smooth_factor=0, closed=False)


def skeleton_contour_intersect_distance(skeleton, contour):
    """
    Compute the distance between the skeleton and the contour at their direct intersection points.
    Core function for midline approximation.
    noted 2023.04.12: renamed from "direct_intersect_distance" to "skeleton_contour_intersect_distance".

    :param skeleton: A numpy array of shape (n, 2) representing the skeleton of a 2D object.
    :param contour: A numpy array of shape (m, 2) representing the contour of a 2D object.
    :return: A numpy array of shape (p,) representing the distances between the skeleton and the contour at their direct intersection points.
    """
    v1, v2 = contour[:-1], contour[1:]
    skel_x, skel_y = skeleton[1:-1].T
    intersect_x, intersect_y = line_contour_intersect_matrix(skeleton[1:-1], contour)
    dx_v1 = intersect_x - v1.T[0][:, np.newaxis]
    dx_v2 = intersect_x - v2.T[0][:, np.newaxis]
    dy_v1 = intersect_y - v1.T[1][:, np.newaxis]
    dy_v2 = intersect_y - v2.T[1][:, np.newaxis]
    dx = dx_v1 * dx_v2
    dy = dy_v1 * dy_v2
    dist_x = skel_x[np.newaxis, :] - intersect_x
    dist_y = skel_y[np.newaxis, :] - intersect_y

    non_boundry_points = np.where(np.logical_and(dy > 0, dx > 0))
    dist_matrix = np.sqrt(dist_x ** 2 + dist_y ** 2)
    dist_matrix[non_boundry_points] = np.inf
    nearest_id_x = np.argsort(dist_matrix, axis=0)[:2]
    nearest_id_y = np.linspace(0, dist_matrix.shape[1] - 1, dist_matrix.shape[1]).astype(int)
    dists = dist_matrix[nearest_id_x[0], nearest_id_y] + dist_matrix[nearest_id_x[1], nearest_id_y]
    return np.concatenate([[0], dists, [0]])


def skeleton_contour_intersect_points(skeleton, contour):
    """
    Compute the midpoint between the skeleton and the contour at their direct intersection points.

    :param skeleton: A numpy array of shape (n, 2) representing the skeleton of a 2D object.
    :param contour: A numpy array of shape (m, 2) representing the contour of a 2D object.
    :return: A numpy array of shape (p, 2) representing the midpoints between the skeleton and the contour at their direct intersection points.
    """
    v1, v2 = contour[:-1], contour[1:]
    skel_x, skel_y = skeleton.T
    intersect_x, intersect_y = line_contour_intersect_matrix(skeleton, contour)
    dx_v1 = intersect_x - v1.T[0][:, np.newaxis]
    dx_v2 = intersect_x - v2.T[0][:, np.newaxis]
    dy_v1 = intersect_y - v1.T[1][:, np.newaxis]
    dy_v2 = intersect_y - v2.T[1][:, np.newaxis]
    dx = dx_v1 * dx_v2
    dy = dy_v1 * dy_v2
    dist_x = skel_x[np.newaxis, :] - intersect_x
    dist_y = skel_y[np.newaxis, :] - intersect_y

    non_boundry_points = np.where(np.logical_and(dy > 0, dx > 0))
    dist_matrix = np.sqrt(dist_x ** 2 + dist_y ** 2)
    dist_matrix[non_boundry_points] = np.inf
    nearest_id_x = np.argsort(dist_matrix, axis=0)[:2]
    nearest_id_y = np.linspace(0, dist_matrix.shape[1] - 1, dist_matrix.shape[1]).astype(int)

    pos1_list = np.array([intersect_x[nearest_id_x[0], nearest_id_y], intersect_y[nearest_id_x[0], nearest_id_y]]).T
    pos2_list = np.array([intersect_x[nearest_id_x[1], nearest_id_y], intersect_y[nearest_id_x[1], nearest_id_y]]).T
    midpoints = (pos1_list + pos2_list) / 2
    d_midpoints = np.abs(midpoints - skeleton)
    outliers = np.where(d_midpoints > 1)
    midpoints[outliers] = skeleton[outliers]
    return midpoints


def measure_along_strip(line, img, width = 1, subpixel = 0.5 ,mode='mean'):
    """
    Measure the intensity along a strip perpendicular to a line in an image.
    :param line: A numpy array of shape (n, 2) representing the line along which to measure intensity.
    :param img: A numpy array of shape (m, p) representing the image in which to measure intensity.
    :param width: A float representing the width of the strip perpendicular to the line.
    :param subpixel: A float representing the subpixel resolution of the strip.
    :param mode: A string representing the method for aggregating intensity values. Options are 'mean', 'max', 'min', and 'median'.
    :return: A numpy array of shape (p,) representing the intensity values along the strip.
    """
    unit_dxy = unit_perpendicular_vector(line, closed=False)
    width_normalized_dxy = unit_dxy * subpixel
    copied_img = img.copy()
    data = bilinear_interpolate_numpy(copied_img, line.T[0], line.T[1])
    for i in range(1, 1+ int(width * 0.5 / subpixel)):
        dxy = width_normalized_dxy * i
        v1 = line + dxy
        v2 = line - dxy
        p1 = bilinear_interpolate_numpy(copied_img, v1.T[0], v1.T[1])
        p2 = bilinear_interpolate_numpy(copied_img, v2.T[0], v2.T[1])
        data = np.vstack([p1, data, p2])

    if mode in ['MAX', 'max', 'max_value']:
        return np.max(data, axis=0)
    elif mode in ['MIN', 'min', 'min_value']:
        return np.min(data, axis=0)
    elif mode in ['MEDIAN', 'Med', 'median', 'med', 'MED']:
        return np.median(data, axis=0)
    else:
        return np.average(data, axis=0)


def orthogonal_mesh(midline, contour, width_list,
                    length=None,
                    median_width=None, scale=2):
    """

    """
    if type(length) not in [float, int]:
        length = measure_length(midline)
    if type(median_width) not in [float, int]:
        median_width = np.median(width_list)

    n_length = int(len(midline) * scale)
    n_width = int(len(midline) * median_width * scale / length)

    edge_points = []
    subpixel_midline = spline_approximation(midline, n=n_length,
                                            smooth_factor=1, closed=False)
    unit_perp = unit_perpendicular_vector(subpixel_midline)

    for i in range(1, len(subpixel_midline) - 1):
        # make core mesh
        p = line_contour_intersection(subpixel_midline[i],
                                      subpixel_midline[i] + unit_perp[i], contour)
        flip = point_line_orientation(subpixel_midline[i], subpixel_midline[i + 1], p[0])
        if flip == -1:
            p = np.flip(p, axis=0)
        edge_points.append(p.flatten())

    edge_points = np.array(edge_points)

    x, y = edge_points[:, 0], edge_points[:, 1]
    dxy = (edge_points[:, 2:] - edge_points[:, :2]) / n_width
    mat = np.tile(np.arange(n_width + 1), (len(edge_points), 1))
    mat_x = x[:, np.newaxis] + mat * dxy[:, 0][:, np.newaxis]
    mat_y = y[:, np.newaxis] + mat * dxy[:, 1][:, np.newaxis]

    return np.array([mat_x, mat_y])

