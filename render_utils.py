'''
Visualization Pipeline for Pulmonai
expects nodboxes , nodsegments, lung_lobe_segmentation, to be present in outputs folder
Output: output_final.json with all the images embedded into it

'''
import os
import vtk
import math
from loguru import logger
import base64
from glob import glob
import SimpleITK as sitk
import json
import unittest.mock as mock
from ast import literal_eval
#from pulmonai.pipelines.classification.tools import classification
from pathlib import Path
import shutil
import sys
sys.path.append('./')
sys.path.append('./pulmonai')

#from loguru import RecordException, logger
#import classification


def get_measurements(labelFile):
    '''
    Calculate volumetric measurements for nodule

    '''
    logger.info('Calculating measurements from segmentation.')
    reader = vtk.vtkNIFTIImageReader()
    reader.SetFileName(labelFile)
    reader.Update()
    (xMin, xMax, yMin, yMax, zMin, zMax) = reader.GetExecutive(
    ).GetWholeExtent(reader.GetOutputInformation(0))
    (xSpacing, ySpacing, zSpacing) = reader.GetOutput().GetSpacing()
    (x0, y0, z0) = reader.GetOutput().GetOrigin()
    # voi = vtk.vtkExtractVOI()
    # voi.SetInputConnection(reader.GetOutputPort())
    # voi.SetVOI(387, 414, 334, 361, 34, 68)
    # voi.Update()
    # print(voi.GetVOI())

    contours = vtk.vtkContourFilter()
    contours.SetInputData(reader.GetOutput())
    contours.SetValue(0, 0.5)
    contours.Update()

    mapper = vtk.vtkPolyDataMapper()

    mapper.SetInputData(contours.GetOutput())
    bbox = vtk.vtkPolyDataConnectivityFilter()
    bbox.SetInputData(contours.GetOutput())
    bbox.SetExtractionModeToLargestRegion()
    bbox.Update()
    # writer = vtk.vtkXMLPolyDataWriter()
    # writer.SetInputData(bbox.GetOutput())
    # writer.SetFileName('/home/arppit/Music/bbox.vtp')
    # writer.Write()
    colors = [(0, 0, 1), (1, 0.5, 0), (0, 1, 0.4),
              (1, 0, 0), (0, 0.2, 0.6), (0.5, 0, 0.2)]
    renderer = vtk.vtkRenderer()

    actor_outline = vtk.vtkActor()
    actor_outline.SetMapper(mapper)
    actor_outline.GetProperty().SetColor(colors[3])
    polyData = vtk.vtkPolyData()
    polyData.DeepCopy(actor_outline.GetMapper().GetInput())
    nSurfacePoints = polyData.GetNumberOfPoints()
    # print(nSurfacePoints)
    (xmin, xmax, ymin, ymax, zmin, zmax) = mapper.GetBounds()
    #print(xmin, xmax, ymin, ymax, zmin, zmax)
    # test = vtk.vtkXMLPolyDataWriter()
    # test.SetInput()
    recist = 0
    recistEndPoint = [[0, 0, 0], [0, 0, 0]]
    #print(int(zmin), int(zmax))
    i = int(zmin)
    try:
        for zi in range(int(zmin), int(zmax)):
            # while(i < int(zmax)):

            z = zi * zSpacing + z0
            #print('z:', i)
            # if z < zmin or z > zmax:
            #     continue
            cutter1 = vtk.vtkCutter()
            cutter1.SetInputData(polyData)
            plane = vtk.vtkPlane()
            plane.SetNormal(0, 0, 1)
            cutter1.SetCutFunction(plane)
            ptOnPlane = [xmin, ymin, z]
            plane.SetOrigin(ptOnPlane)
            try:
                cutter1.Update()
            except:
                pass
            #print('planePoints', ptOnPlane)
            cutPoly = cutter1.GetOutput()
            cutPoints = cutPoly.GetPoints()
            #print('cutpoints;', cutPoints)
            npoints = cutPoly.GetNumberOfPoints()
            cutPolyBounds = cutPoly.GetBounds()
            maxPossible = (cutPolyBounds[0] - cutPolyBounds[1]) * (cutPolyBounds[0] - cutPolyBounds[1]) + \
                (cutPolyBounds[2] - cutPolyBounds[3]) * \
                (cutPolyBounds[2] - cutPolyBounds[3])
            #print('last:', cutPoints, npoints, maxPossible)
            #del cutter1, plane
            #print('cutpoly', maxPossible,npoints)

            if maxPossible < recist:
                continue
            for i in range(0, npoints):
                p1 = cutPoints.GetPoint(i)
                #print('cutpoints', test)
                for j in range(i, npoints):
                    p2 = cutPoints.GetPoint(j)
                    d = vtk.vtkMath.Distance2BetweenPoints(p1, p2)
                    if d > recist:
                        recist = d
                        recistEndPoint[0][0] = p1[0]
                        recistEndPoint[0][1] = p1[1]
                        recistEndPoint[0][2] = p1[2]
                        recistEndPoint[1][0] = p2[0]
                        recistEndPoint[1][1] = p2[1]
                        recistEndPoint[1][2] = p2[2]
                        recistLength = (recistEndPoint[1][0] - recistEndPoint[0][0])**2 + (recistEndPoint[1]
                                                                                           [1] - recistEndPoint[0][1])**2 + (recistEndPoint[1][2] - recistEndPoint[0][2])**2

                        recistLength = math.sqrt(abs(recistLength))
        #vtkmassproperties <-polydata
        # update
        # getVolume ...
        mass = vtk.vtkMassProperties()
        mass.SetInputData(polyData)
        volume = mass.GetVolume()
        surface = mass.GetSurfaceArea()
        logger.info('RecistLength:', recistLength,
                    'Volume:', volume, 'Surface:', surface)
        # print(recistEndPoint)
        renderer.AddActor(actor_outline)
        camera = renderer.GetActiveCamera()
        camera.SetFocalPoint(0, 0, 0)

        camera.SetPosition(0, 0, 1)  # Camera in Z so it display XY planes.
        camera.SetViewUp(0, 1, 0)
        renderer.ResetCamera()
        renderer.ResetCameraClippingRange()
        window = vtk.vtkRenderWindow()
        window.AddRenderer(renderer)
        window.SetSize(1024, 1024)
        window.Render()
        return {'RecistLength': recistLength, 'Volume': volume, 'Surface': surface, 'Endpoint': recistEndPoint}
    except:
        logger.warning('Single pixle segmentation skipping ...')
        return {'RecistLength': 0, 'Volume': 0, 'Surface': 0, 'Endpoint': 0}
# this function  is under construction


def checkBvsM(img):
    # '''
    # classify the nodule as benign vs malignant
    # input: PIL images to be inferenced
    # output:str Lable
    # '''
    cl = classification.malignancy(img)
    #lables = ['Benign','Malignant']
    return cl


def checkText(img):
    # '''
    # classify nodule image as GCN, Part-Solid, Solid
    # input: PIL images to be inferenced
    # output:str Lable
    # '''
    cl = classification.texture(img)
    #lables = ['GCN','Part-Solid','Solid']
    return cl


def get_cube_actor(flip=True):
    # Returns vtkannotatedCubeActor
    #
    axesActor = vtk.vtkAnnotatedCubeActor()
    axesActor.SetXPlusFaceText('L')
    axesActor.SetXMinusFaceText('R')
    axesActor.SetYMinusFaceText('A')
    axesActor.SetYPlusFaceText('P')
    axesActor.SetZMinusFaceText('S')
    axesActor.SetZPlusFaceText('I')
    if flip:
        axesActor.SetXFaceTextRotation(180)
        axesActor.SetZFaceTextRotation(180)
        axesActor.SetYFaceTextRotation(180)

    axesActor.GetTextEdgesProperty().SetColor(1, 1, 0)
    axesActor.GetCubeProperty().SetColor(0, 0, 1)
    return axesActor


def get_b64_image(window, image_name, temp_dirr):
    w2if = vtk.vtkWindowToImageFilter()
    w2if.SetInput(window)
    w2if.Update()
    writer = vtk.vtkPNGWriter()
    #os.makedirs(temp_dirr+'/temp', exist_ok= True)
    print(f'{temp_dirr}/{image_name}')
    writer.SetFileName(f'{temp_dirr}/{image_name}')
    writer.SetInputData(w2if.GetOutput())
    writer.Write()
    with open(f'{temp_dirr}/{image_name}', 'rb') as img1:
        f = img1.read()
        imagedata1 = {"mimeType": "image/jpg",
                      "content": " ",
                      "fileName": f"{image_name}"
                      }
        imagedata1["content"] = base64.b64encode((f)).decode("utf-8")
    # shutil.rmtree(temp_dirr)
    # shutil.rmtree(f'{dirr}temp')
    return imagedata1


def save_image(window, image_name, temp_dirr, json=False):
    w2if = vtk.vtkWindowToImageFilter()
    w2if.SetInput(window)
    w2if.Update()
    writer = vtk.vtkPNGWriter()
    #os.makedirs(temp_dirr+'/temp', exist_ok= True)
    print(f' Saving {image_name} in {temp_dirr}/{image_name}')
    writer.SetFileName(f'{temp_dirr}/{image_name}')
    writer.SetInputData(w2if.GetOutput())
    writer.Write()
    return 'SUCCESS'


def generate_window(renderer, orientation, output_file):
    file_name = 'VR_Heart'
    window = vtk.vtkRenderWindow()
    window.SetSize(1024, 1024)
    window.AddRenderer(renderer)
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(window)
    interactor.Initialize()
    axesActor = get_cube_actor_2()
    axes = vtk.vtkOrientationMarkerWidget()
    axes.SetOrientationMarker(axesActor)
    axes.SetInteractor(interactor)
    axes.EnabledOn()
    axes.InteractiveOn()
    interactor.Start()
    window.Render()
    if orientation == 'P':
        # interactor.Start()
        imagedata1 = save_image(
            window, f"{file_name}_posterior.png", output_file, json=False)
        print(imagedata1)
    if orientation == 'A':
        imagedata1 = save_image(
            window, f"{file_name}_anterior.png", output_file, json=False)
        print(imagedata1)
    if orientation == 'L':
        imagedata1 = save_image(
            window, f"{file_name}_left.png", output_file, json=False)
        print(imagedata1)
    if orientation == 'R':
        imagedata1 = save_image(
            window, f"{file_name}_right.png", output_file, json=False)
        print(imagedata1)
    if orientation == 'S':
        imagedata1 = save_image(
            window, f"{file_name}_superior.png", output_file, json=False)
        print(imagedata1)
    if orientation == 'I':
        imagedata1 = save_image(
            window, f"{file_name}_inferior.png", output_file, json=False)
        print(imagedata1)


def get_cube_actor(flip=True):
    # Returns vtkannotatedCubeActor
    #
    axesActor = vtk.vtkAnnotatedCubeActor()
    axesActor.SetXPlusFaceText('L')
    axesActor.SetXMinusFaceText('R')
    axesActor.SetYMinusFaceText('A')
    axesActor.SetYPlusFaceText('P')
    axesActor.SetZMinusFaceText('S')
    axesActor.SetZPlusFaceText('I')
    if flip:
        axesActor.SetXFaceTextRotation(180)
        axesActor.SetZFaceTextRotation(180)
        axesActor.SetYFaceTextRotation(180)

    # axesActor.GetTextEdgesProperty().SetColor(0, 0, 0)
    # axesActor.GetXPlusFaceProperty().SetColor(1, 0, 0)
    # axesActor.GetXMinusFaceProperty().SetColor(1, 0, 0)
    # axesActor.GetYPlusFaceProperty().SetColor(0, 1, 0)
    # axesActor.GetYMinusFaceProperty().SetColor(0, 1, 0)
    # axesActor.GetZPlusFaceProperty().SetColor(0, 0, 1)
    # axesActor.GetZMinusFaceProperty().SetColor(0, 0, 1)
    # axesActor.GetCubeProperty().SetColor(0,0,0)
    axesActor.GetCubeProperty().SetOpacity(0)
    return axesActor


def get_cube_actor_2():
    orientMarkerCubeProp = get_cube_actor()
    cubeSource = vtk.vtkCubeSource()
    cubeSource.Update()
    faceColors = vtk.vtkUnsignedCharArray()
    faceColors.SetNumberOfComponents(3)
    faceColors.InsertNextTuple3(255, 0, 0)
    faceColors.InsertNextTuple3(255, 0, 0)
    faceColors.InsertNextTuple3(0, 255, 0)
    faceColors.InsertNextTuple3(0, 255, 0)
    faceColors.InsertNextTuple3(0, 0, 255)
    faceColors.InsertNextTuple3(0, 0, 255)
    cubeSource.GetOutput().GetCellData().SetScalars(faceColors)
    cubeSource.Update()
    cubeMapper = vtk.vtkPolyDataMapper()
    cubeMapper.SetInputData(cubeSource.GetOutput())
    cubeMapper.Update()
    cubeActor = vtk.vtkActor()
    cubeActor.SetMapper(cubeMapper)
    propAssembly = vtk.vtkPropAssembly()
    propAssembly.AddPart(orientMarkerCubeProp)
    propAssembly.AddPart(cubeActor)
    return propAssembly


def set_camera_orientation(renderer, orientation):
    camera = renderer.GetActiveCamera()
    if orientation == 'P':
        camera.SetFocalPoint(0, -1, 0)
        camera.SetPosition(0, 1, 0)
        camera.SetViewUp(0, 0, -1)
        renderer.ResetCamera()
        renderer.ResetCameraClippingRange()
        return renderer
    if orientation == 'L':
        camera.SetFocalPoint(-1, 0, 0)
        camera.SetPosition(1, 0, 0)
        camera.SetViewUp(0, 0, -1)
        renderer.ResetCamera()
        return renderer
    if orientation == 'A':
        camera.SetFocalPoint(0, 1, 0)
        camera.SetPosition(0, -1, 0)
        camera.SetViewUp(0, 0, -1)
        renderer.ResetCamera()
        return renderer
    if orientation == 'R':
        camera.SetFocalPoint(1, 0, 0)
        camera.SetPosition(-1, 0, 0)
        camera.SetViewUp(0, 0, -1)
        renderer.ResetCamera()
        return renderer
    if orientation == 'S':
        camera.SetFocalPoint(0, 0, 1)
        camera.SetPosition(0, 0, -1)
        camera.SetViewUp(1, 0, 0)
        renderer.ResetCamera()
        return renderer
    if orientation == 'I':
        camera.SetFocalPoint(0, 0, 1)
        camera.SetPosition(0, 0, -1)  # Camera in Z so it display XY planes.
        camera.SetViewUp(1, 0, 0)
        renderer.ResetCamera()
        return renderer


def volume_rendering_h(ctFile, label_file, work_dir):
    convert_img = sitk.ReadImage(ctFile)
    img2 = sitk.FlipImageFilter()
    img2.SetFlipAxes([False, True, False])
    flippedimg = img2.Execute(convert_img)
    newCTfilename = f'{work_dir}/temp_0000.mhd'
    sitk.WriteImage(flippedimg, newCTfilename)
    reader = vtk.vtkMetaImageReader()
    reader.SetFileName(newCTfilename)
    reader.Update()
    mask_p = f'{label_file}'
    convert_mask = sitk.ReadImage(mask_p)
    img2 = sitk.FlipImageFilter()
    img2.SetFlipAxes([False, True, False])
    flippedimg = img2.Execute(convert_mask)
    # os.makedirs(f'{rootf}/initial_inputs/temp/', exist_ok=True)
    #temp_dirr = f'{work_dir}'
    newMaskfilename = f'{work_dir}/heart_mask.mhd'
    sitk.WriteImage(flippedimg, newMaskfilename)
    mreader = vtk.vtkMetaImageReader()
    mreader.SetFileName(newMaskfilename)
    mreader.Update()
    thresh = vtk.vtkImageThreshold()
    thresh.SetInputConnection(mreader.GetOutputPort())
    thresh.ThresholdBetween(-0.5, 0.5)
    thresh.ReplaceInOn()
    thresh.SetInValue(0)
    thresh.ReplaceOutOn()
    thresh.SetOutValue(1)
    thresh.Update()
    vol = vtk.vtkGPUVolumeRayCastMapper()
    vol.SetInputConnection(reader.GetOutputPort())
    vol.SetMaskTypeToBinary()
    # vol.SetMaskInput(mreader.GetOutput())
    vol.Update()
    volume = vtk.vtkVolume()
    volume.SetMapper(vol)
    otf = vtk.vtkPiecewiseFunction()
    otf.AddPoint(-2048, 0, 0.5, 0)
    otf.AddPoint(-142.68, 0, 0.5, 0)
    otf.AddPoint(145.2, 0.12, 0.5, 0)
    otf.AddPoint(192.17, 0.56, 0.5, 0)
    otf.AddPoint(217.24, 0.78, 0.5, 0)
    otf.AddPoint(384.35, 0.83, 0.5, 0)
    otf.AddPoint(3661, 0.83, 0.5, 0)
    volume.GetProperty().SetScalarOpacity(otf)
    # AddPoint (double x, double y, double midpoint, double sharpness)
    ctf = vtk.vtkColorTransferFunction()
    ctf.AddRGBPoint(-2048, 0/255, 0/255, 0)
    ctf.AddRGBPoint(-142.68, 0/255, 0/255, 0)
    ctf.AddRGBPoint(145.2,  157/255, 0/255, 4/255)
    ctf.AddRGBPoint(192.17, 232/255, 116/255, 0/255)
    ctf.AddRGBPoint(217.24, 248/255, 206/255, 116/255)
    ctf.AddRGBPoint(384.35, 232/255, 232/255, 1)
    ctf.AddRGBPoint(3661, 1, 1, 1)
    volume.GetProperty().SetColor(ctf)
    volume.GetProperty().SetScalarOpacityUnitDistance(0.12)
    volume.GetProperty().SetSpecular(0.1)
    volume.GetProperty().SetShade(1)
    volume.GetProperty().SetAmbient(0.2)
    volume.GetProperty().ShadeOn()
    volume.GetProperty().SetDiffuse(1)
    # volume.GetProperty().SetInterpolation(1)
    # volume.GetProperty().ShadeOn()
    # <VolumeProperty selected="false" hideFromEditors="false" name="CT-Coronary-Arteries-2" gradientOpacity="4 0 1 255 1" userTags="" specularPower="1" scalarOpacity="14 -2048 0 142.677 0 145.016 0.116071 192.174 0.5625 217.24 0.776786 384.347 0.830357 3661 0.830357" id="vtkMRMLVolumePropertyNode11" specular="0" shade="1" ambient="0.2" colorTransfer="28 -2048 0 0 0 142.677 0 0 0 145.016 0.615686 0 0.0156863 192.174 0.909804 0.454902 0 217.24 0.972549 0.807843 0.611765 384.347 0.909804 0.909804 1 3661 1 1 1" selectable="true" diffuse="1" interpolation="1" effectiveRange="142.677 384.347"/>
    gtf = vtk.vtkPiecewiseFunction()
    gtf.AddPoint(0, 1.00, 0.5, 0.0)
    gtf.AddPoint(255, 1, 0.5, 0)
    volume.GetProperty().SetGradientOpacity(gtf)
    ren = vtk.vtkRenderer()
    ren.AddVolume(volume)
    ren.RemoveAllLights()
    light_kit = vtk.vtkLightKit()
    light_kit.SetKeyLightIntensity(1.0)
    light_kit.AddLightsToRenderer(ren)
    imagef = {}
    file_name = 'heart_vrt'
    name = 'ct_001'
    orientations = 'LRAPSI'
    for orientation in orientations:
        renderer = set_camera_orientation(ren, orientation)
        generate_window(renderer, orientation, work_dir)
        del renderer
    # # from back to chest
    # camera.SetFocalPoint(0, -1, 0)
    # camera.SetPosition(0, 1, 0)  # Camera in Z so it display XY planes.
    # camera.SetViewUp(0, 0, -1)
    # renderer.ResetCameraClippingRange()
    # renderer.ResetCamera()

    #get_LRAPSI_orientataion(ren, work_dir)
    # interactor.Start()


def save_aorta(labelFileName):
    reader_label = vtk.vtkNIFTIImageReader()
    reader_label.SetFileName(labelFileName)
    reader_label.Update()
    colors = [(0, 0, 1), (1, 0.5, 0), (0, 1, 0.4),
              (1, 0, 0), (0, 0.2, 0.6), (0.5, 0, 0.2), (1, 0, 0)]
    renderer = vtk.vtkRenderer()
    # for t in range(7, 8):
    thresh = vtk.vtkImageThreshold()
    thresh.SetInputConnection(reader_label.GetOutputPort())
    thresh.ThresholdBetween(6.5, 7.5)
    thresh.ReplaceInOn()
    thresh.SetInValue(1)
    thresh.ReplaceOutOn()
    thresh.SetOutValue(0)
    thresh.Update()
    contours = vtk.vtkContourFilter()
    contours.SetInputData(thresh.GetOutput())
    contours.SetValue(0, 0.5)
    contours.ComputeScalarsOff()
    contours.ComputeNormalsOn()
    contours.Update()
    mapper = vtk.vtkPolyDataMapper()

    mapper.SetInputData(contours.GetOutput())
    mapper.SetResolveCoincidentTopologyToPolygonOffset()
    mapper.SetScalarVisibility(False)
    writer = vtk.vtkXMLPolyDataWriter()
    writer.SetFileName('C:\\Users\\Arppit\\Documents\\Arduino\\check.vtp')
    writer.SetInputData(contours.GetOutput())
    writer.Write()
    actor_outline = vtk.vtkActor()
    actor_outline.SetMapper(mapper)
    actor_outline.GetProperty().SetColor((1, 0, 0))
    renderer.AddActor(actor_outline)
    window = vtk.vtkRenderWindow()
    window.SetSize(1024, 1024)
    window.AddRenderer(renderer)
    window.Render()
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(window)
    interactor.Initialize()
    interactor.Start()


def render_image3d(labelFileName, outputFolder, name):
    '''
    labelFileName : path to input label.nii.gz
    outputFolder : dirname for saving screenshots
    '''
    logger.info('[START] Generating 3d screenshot')
    f = outputFolder
    if outputFolder == './':
        f = f'{os.path.abspath(__file__)}/screenshots'
    # suppose fname is 'home/pulmonai/pumonai/lndb201.mhd this sets file_name as lndb201'
    file_name = labelFileName.split('/')[-1].split('.')[0]
    reader_label = vtk.vtkNIFTIImageReader()
    reader_label.SetFileName(labelFileName)
    reader_label.Update()
    colors = [(0, 0, 1), (1, 0.5, 0), (0, 1, 0.4),
              (1, 0, 0), (0, 0.2, 0.6), (0.5, 0, 0.2)]
    renderer = vtk.vtkRenderer()

    for t in range(1, 7):
        thresh = vtk.vtkImageThreshold()
        thresh.SetInputConnection(reader_label.GetOutputPort())
        thresh.ThresholdBetween(t - 0.5, t + 0.5)
        thresh.ReplaceInOn()
        thresh.SetInValue(1)
        thresh.ReplaceOutOn()
        thresh.SetOutValue(0)
        thresh.Update()
        contours = vtk.vtkContourFilter()
        contours.SetInputData(thresh.GetOutput())
        contours.SetValue(0, 0.5)
        contours.ComputeScalarsOff()
        contours.ComputeNormalsOn()
        contours.Update()
        mapper = vtk.vtkPolyDataMapper()

        mapper.SetInputData(contours.GetOutput())
        mapper.SetResolveCoincidentTopologyToPolygonOffset()
        mapper.SetScalarVisibility(False)

        actor_outline = vtk.vtkActor()
        actor_outline.SetMapper(mapper)
        actor_outline.GetProperty().SetColor(colors[t - 1])
        renderer.AddActor(actor_outline)
    # return renderer
    imagef = {}
    camera = renderer.GetActiveCamera()

    # # from back to chest
    camera.SetFocalPoint(0, -1, 0)
    camera.SetPosition(0, 1, 0)  # Camera in Z so it display XY planes.
    camera.SetViewUp(0, 0, -1)
    renderer.ResetCamera()
    renderer.ResetCameraClippingRange()
    renderer.ResetCamera()
    window = vtk.vtkRenderWindow()
    window.SetSize(1024, 1024)
    window.AddRenderer(renderer)
    window.Render()
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(window)
    interactor.Initialize()
    axesActor = get_cube_actor()
    axes = vtk.vtkOrientationMarkerWidget()
    axes.SetOrientationMarker(axesActor)
    axes.SetInteractor(interactor)
    axes.EnabledOn()
    axes.InteractiveOn()
    interactor.Start()
    #imagedata1 = get_b64_image(window, f"{file_name}_{name}_posterior.png", f)
    #imagef['A'] = imagedata1
    # interactor = vtk.vtkRenderWindowInteractor()
    # interactor.SetRenderWindow(window)
    # interactor.Initialize()
    # interactor.Start()
    del window, camera, interactor, imagedata1
    # left lung
    camera = renderer.GetActiveCamera()
    camera.SetFocalPoint(-1, 0, 0)
    camera.SetPosition(1, 0, 0)  # Camera in Z so it display XY planes.
    camera.SetViewUp(0, 0, -1)
    renderer.ResetCamera()
    window = vtk.vtkRenderWindow()
    window.SetSize(1024, 1024)
    window.AddRenderer(renderer)
    window.Render()
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(window)
    interactor.Initialize()
    axesActor = get_cube_actor()
    axes = vtk.vtkOrientationMarkerWidget()
    axes.SetOrientationMarker(axesActor)
    axes.SetInteractor(interactor)
    axes.EnabledOn()
    axes.InteractiveOn()
    imagedata1 = get_b64_image(window, f"{file_name}_{name}_left.png", f)
    interactor.Start()
    imagef['L'] = imagedata1
    del window, imagedata1, interactor
    # from chest to back
    camera.SetFocalPoint(0, 1, 0)
    camera.SetPosition(0, -1, 0)  # Camera in Z so it display XY planes.
    camera.SetViewUp(0, 0, -1)
    renderer.ResetCamera()
    window = vtk.vtkRenderWindow()
    window.SetSize(1024, 1024)
    window.AddRenderer(renderer)
    window.Render()
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(window)
    interactor.Initialize()
    axesActor = get_cube_actor()
    axes = vtk.vtkOrientationMarkerWidget()
    axes.SetOrientationMarker(axesActor)
    axes.SetInteractor(interactor)
    axes.EnabledOn()
    axes.InteractiveOn()
    imagedata1 = get_b64_image(window, f"{file_name}_{name}_anterior.png", f)
    # interactor.Start()
    imagef['P'] = imagedata1
    del window, imagedata1, interactor
    # right lung
    camera.SetFocalPoint(1, 0, 0)
    camera.SetPosition(-1, 0, 0)  # Camera in Z so it display XY planes.
    camera.SetViewUp(0, 0, -1)
    renderer.ResetCamera()
    window = vtk.vtkRenderWindow()
    window.SetSize(1024, 1024)
    window.AddRenderer(renderer)
    window.Render()
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(window)
    interactor.Initialize()
    axesActor = get_cube_actor()
    axes = vtk.vtkOrientationMarkerWidget()
    axes.SetOrientationMarker(axesActor)
    axes.SetInteractor(interactor)
    axes.EnabledOn()
    axes.InteractiveOn()
    imagedata1 = get_b64_image(window, f"{file_name}_{name}_right.png", f)
    # interactor.Start()
    imagef['R'] = imagedata1
    del window, imagedata1

    logger.info('[SUCCESS] Saved 3D image')
    return imagef


def render_vtp(labelfile):
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(labelfile)
    reader.Update()
    renderer = vtk.vtkRenderer()
    contours = vtk.vtkContourFilter()
    contours.SetInputData(reader.GetOutput())
    contours.SetValue(0, 0.5)
    contours.ComputeScalarsOff()
    contours.ComputeNormalsOn()
    contours.Update()
    mapper = vtk.vtkPolyDataMapper()

    mapper.SetInputData(reader.GetOutput())
    mapper.SetResolveCoincidentTopologyToPolygonOffset()
    mapper.SetScalarVisibility(False)

    actor_outline = vtk.vtkActor()
    actor_outline.SetMapper(mapper)
    actor_outline.GetProperty().SetColor([1, 0, 0])
    renderer.AddActor(actor_outline)
    window = vtk.vtkRenderWindow()
    window.SetSize(1024, 1024)
    window.AddRenderer(renderer)
    window.Render()
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(window)
    interactor.Initialize()
    interactor.Start()


def save_images(ctFileName, labelFileName, outputFolder, measurements):
    '''
    These is like a  wrapper function 
    '''
    logger.info('[START] Begin rendering image slices')
    #save_nodule_image(ctFileName, labelFileName, 'coronal', outputFolder)
    nodule_axial = save_nodule_image(ctFileName, labelFileName, 'axial',
                                     outputFolder, measurements)
    #save_nodule_image(ctFileName, labelFileName, 'sagittal', outputFolder)
    logger.info(
        f'[SUCCESS] Saved image slices in Coronal, Axial, Sagittal orientations in {outputFolder}')
    logger.info('[START] Begin rendering segmentation volume')
    nodule_3d_images = render_image3d(labelFileName, outputFolder, 'nodule')
    #lung_3d_images = render_image3d(lung_label,outputFolder,'nodule')
    logger.info(
        f'[SUCCESS] Saved Left, Right, Anterior, & Posterior Veiws of segmentation volume in {outputFolder}')
    logger.info('[FINISHED] Script Executed Successfully')
    return nodule_3d_images, nodule_axial


def main():
    # This function looks for all the generated nodule_ct and nodule_seg and then generates images and adds it to the json'
    dirr = os.path.abspath(__file__)
    #rootf ='/'.join(dirr.split('/')[:-3])
    #rootf = '/data1/repositories/work/pulmonai'
    rootf = os.environ['data_dir']
    logger.info(f'Looking for intermediate json file in {rootf}/outputs')
    # print(rootf)
    # /data
    info = []
    new_json = {'nodules': {}}
    json_dir = f'{rootf}/outputs/'
    f = open(f'{json_dir}output.json')
    r = json.loads(f.read())
    logger.info(f'Finished reading json file. Begin inserting images')
    nodules = literal_eval(r)
    for ind in nodules['results']:
        sid = ind['seriesId']
        logger.info(f'=> Generating visualizations for {sid}')
        ct_path = f'{rootf}/outputs/initial/nodbox_{sid}/'
        seg_path = f'{rootf}/outputs/initial/nodsegs_{sid}/'
        seg_files = glob(seg_path + "*.nii.gz")
        ct_files = glob(ct_path + '*.nii.gz')
        # print(ct_files)
        kkk = 0
        for i in ct_files:
            dirr = Path(os.path.abspath(__file__)).parent
            output = os.makedirs(f'{dirr}/nodules', exist_ok=True)
            output = os.makedirs(f'{dirr}/nodules/{sid}/', exist_ok=True)
            output = f'{dirr}/nodules/{sid}/'
            outputf = os.makedirs(
                f'{dirr}/nodules/{sid}/{i.split(".")[0]}', exist_ok=True)
            ctfileName = f'{i}'
            name = i.split('/')[-1].split('_')[1]
            #print('*'*50, name)
            labelFile = f'{seg_path}seg{name}'
            outputFolder = f'{dirr}/nodules/{name}'
            logger.info(
                f'Looking for label file in {seg_path}. Presnt: {os.path.isfile(f"{seg_path}seg{name}")} ')
            # print(labelFile)
            measurements = get_measurements(labelFile)
            #measurements = {'Volume':2, 'RecistLength':3, 'Surface':2}
            nodule3dimages, nodule_info = save_images(
                ctfileName, labelFile, outputFolder, measurements)
            #print(int(name) <=5)

            nodule = mock.Mock()
            nodule.Volume = measurements['Volume']
            nodule.Max_2D_diameter = measurements['RecistLength']
            nodule.Max_Surface = measurements['Surface']
            nodule.Finding = 'Pulmonary Nodule'
            nodule.nodule_with_measurement = []
            for ke in nodule_info.keys():
                ind['nodule_details'][kkk][ke] = nodule_info[ke]
            ind['nodule_details'][kkk]['3D_images'] = [nodule3dimages]
            rf = os.environ['data_dir']
            lobeF = f'{rootf}/outputs/coarse_lung_lobe_segmentation_{sid}_0000.nii.gz'
            logger.info(f'generating lung lobe segmentations for case {sid}')
            lungLobeImages = render_image3d(lobeF, outputFolder, 'lung')
            ind['lobe_details']['lobe_segmentation_images'] = lungLobeImages
            dict = {'Volume in mm3': nodule.Volume, 'RECIST length': nodule.Max_2D_diameter,
                    'Max Surface Area': nodule.Max_Surface, 'nodule_with_measurements': nodule.nodule_with_measurement}

            #nodules[iter][int(name)]['nodule_info'] = dict

            #ind['nodule_details'][kkk]['nodules_with_measurements'] = dict
            kkk += 1
            #new_json['nodules'][int(name)] = dict
        inputctfile = sid
        logger.info(f'Begin Volume rendering for {inputctfile}')
        ind['nodule visuals'] = volume_rendering(inputctfile)
    logger.info(f'Finished Volume rendering for {inputctfile}')
    # shutil.rmtree(f'{dirr}/nodules')
    with open(f'{rootf}/outputs'+'/output_final.json', 'w') as jsonfile:
        json.dump(nodules, jsonfile)
    logger.info(
        '[FINISHED] Finished generating images. Script ended successfully.')
    #nodules_info = generate(measurements)
    # nfo.append(nodules_info)


def save_nodule_image(ctFileName, labelFileName, orientation, outputF, measurement):
    # '''
    # Saves the axial slice of nodule with contour overlay and its recist measurement

    # '''
    reader = vtk.vtkNIFTIImageReader()
    reader.SetFileName(ctFileName)
    reader.Update()
    print('reader:', reader.GetOutput().GetBounds())
    # Matrices for axial, coronal, sagittal, oblique view orientations
    (xMin, xMax, yMin, yMax, zMin, zMax) = reader.GetExecutive(
    ).GetWholeExtent(reader.GetOutputInformation(0))
    (xSpacing, ySpacing, zSpacing) = reader.GetOutput().GetSpacing()
    (x0, y0, z0) = reader.GetOutput().GetOrigin()

    center = [x0 + xSpacing * 0.5 * (xMin + xMax), y0 + ySpacing * 0.5 *
              (yMin + yMax), z0 + zSpacing * 0.5 * (zMin + zMax)]
    print(measurement)
    axial = vtk.vtkMatrix4x4()
    if measurement['Endpoint'] == 0:
        axial.DeepCopy((1, 0, 0, x0,
                        0, 1, 0, y0,
                        0, 0, 1, z0,
                        0, 0, 0, 1))
    else:

        axial.DeepCopy((1, 0, 0, x0,
                        0, 1, 0, y0,
                        0, 0, 1, measurement['Endpoint'][0][2],
                        0, 0, 0, 1))

    reslice = vtk.vtkImageReslice()
    reslice.SetInputConnection(reader.GetOutputPort())
    reslice.SetOutputDimensionality(2)
    reslice.SetResliceAxes(axial)

    reslice.SetOutputDimensionality(2)

    reslice.SetInterpolationModeToLinear()
    # map to window image level colors

    color = vtk.vtkImageMapToWindowLevelColors()
    color.SetLevel(-700)
    color.SetWindow(1500)
    color.SetInputConnection(reslice.GetOutputPort())
    color.Update()
    # Display the image
    actor = vtk.vtkImageActor()
    actor.GetMapper().SetInputConnection(color.GetOutputPort())
    print(color.GetOutput().GetBounds())
    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)

    camera = renderer.GetActiveCamera()
    camera.SetFocalPoint(0, 0, 0)

    camera.SetPosition(0, 0, -1)  # Camera in Z so it display XY planes.
    camera.SetViewUp(0, -1, 0)
    renderer.ResetCamera()
    renderer.ResetCameraClippingRange()

    reader_label = vtk.vtkNIFTIImageReader()
    reader_label.SetFileName(labelFileName)
    reader_label.Update()
    reslice_label = vtk.vtkImageReslice()
    reslice_label.SetInputConnection(reader_label.GetOutputPort())
    reslice_label.SetOutputDimensionality(2)

    reslice_label.SetResliceAxes(axial)
    reslice_label.SetInterpolationModeToNearestNeighbor()

    # reslice_label.SetResliceAxes(axial)
    reslice_label.SetInterpolationModeToNearestNeighbor()
    reslice_label.Update()
    actor = vtk.vtkImageActor()
    actor.GetMapper().SetInputConnection(color.GetOutputPort())

    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)

    camera = renderer.GetActiveCamera()
    camera.SetFocalPoint(0, 0, 0)

    camera.SetPosition(0, 0, -1)  # Camera in Z so it display XY planes.
    camera.SetViewUp(0, -1, 0)
    renderer.ResetCamera()
    renderer.ResetCameraClippingRange()
    window = vtk.vtkRenderWindow()
    window.SetSize(1024, 1024)
    window.AddRenderer(renderer)
    window.Render()

    #screenshot_image_slice(window, ctFileName, 'inference', outputF)
    os.makedirs(outputF+'/temp', exist_ok=True)
    f = outputF+'/temp'
    file_name = ctFileName.split('/')[-1].split('.')[0]
    imagedata1 = get_b64_image(
        window, f"{file_name}_axial_at_recist_length.png", f)
    fname = f'{f}/{file_name}_axial_at_recist_length.png'
    del window, renderer
    images = [imagedata1]
    bm = checkBvsM(Path(fname))
    t = checkText(Path(fname))
    #renderer = vtk.vtkRenderer()
    reslice_label = vtk.vtkImageReslice()
    reslice_label.SetInputConnection(reader_label.GetOutputPort())
    reslice_label.SetOutputDimensionality(2)

    reslice_label.SetResliceAxes(axial)
    reslice_label.SetInterpolationModeToNearestNeighbor()

    # reslice_label.SetResliceAxes(axial)
    reslice_label.SetInterpolationModeToNearestNeighbor()
    reslice_label.Update()
    actor = vtk.vtkImageActor()
    actor.GetMapper().SetInputConnection(color.GetOutputPort())

    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)

    camera = renderer.GetActiveCamera()
    camera.SetFocalPoint(0, 0, 0)

    camera.SetPosition(0, 0, -1)  # Camera in Z so it display XY planes.
    camera.SetViewUp(0, -1, 0)
    renderer.ResetCamera()
    renderer.ResetCameraClippingRange()
    contours = vtk.vtkContourFilter()
    contours.SetInputData(reslice_label.GetOutput())
    contours.SetValue(0, 0.5)
    contours.Update()

    mapper = vtk.vtkPolyDataMapper()

    mapper.SetInputData(contours.GetOutput())
    mapper.SetResolveCoincidentTopologyToPolygonOffset()
    mapper.SetScalarVisibility(False)
    actor_outline = vtk.vtkActor()
    actor_outline.SetMapper(mapper)
    # actor_outline.GetMapper().SetInputConnection(color.GetOutputPort())
    actor_outline.GetProperty().SetColor(255, 0, 0)
    actor_outline.GetProperty().SetLineWidth(4)
    renderer.AddActor(actor_outline)
    # renderer.AddActor(actor)
    renderer.ResetCamera()
    norm_coord = vtk.vtkCoordinate()
    norm_coord.SetCoordinateSystemToWorld()
    norm_coord.SetCoordinateSystemToNormalizedViewport()
    window = vtk.vtkRenderWindow()

    window.SetSize(1024, 1024)
    if measurement['Endpoint'] != 0:
        rep = vtk.vtkAxisActor2D()

        rep.GetPoint1Coordinate().SetCoordinateSystemToWorld()
        rep.GetPoint1Coordinate().SetValue(measurement['Endpoint'][0])
        rep.GetPoint2Coordinate().SetCoordinateSystemToWorld()
        rep.GetPoint2Coordinate().SetValue(measurement['Endpoint'][1])
        # rep.SetPoint1(measurement['Endpoint'][0])
        # rep.SetPoint2WorldPosition(measurement['Endpoint'][1])
        rep.SetLabelVisibility(0)
        rep.SetNumberOfLabels(2)
        rep.SetTickLength(1)
        rep.SetTitlePosition(1)
        rep.GetTitleTextProperty().SetFontSize(0)

        rep.SetTitle(str(round(measurement['RecistLength'], 2)))
        rep.GetProperty().SetColor(0, 0, 1)
        renderer.AddActor(rep)
        print('check2')
    window.AddRenderer(renderer)
    window.Render()
    file_name = ctFileName.split('/')[-1].split('.')[0]
    imagedata2 = get_b64_image(
        window, f"{file_name}_axial_with_overlay.png", f)
    images.append(imagedata2)
    temp = {}
    temp['Nodule Classification'] = bm
    temp['Nodule Texture'] = t
    temp['Nodule_image'] = images
    logger.info('Done generating 2D images')
    shutil.rmtree(outputF+'/temp')
    return temp


if __name__ == '__main__':
    # main()
    # render_image3d('C:\\Users\\Arppit\\Documents\\Arduino\\WHS_cropct2_0000.nii.gz_cropct2_0000.nii.gz',
    #                'C:\\Users\\Arppit\\Documents\\Arduino', 'heart_seg')
    volume_rendering_h('C:\\Users\\Arppit\\Documents\\Arduino\\cropct1_0000.nii.gz',
                       'C:\\Users\\Arppit\\Documents\\Arduino\\WHS_cropct2_0000.nii.gz_cropct2_0000.nii.gz', 'C:\\Users\\Arppit\\Documents\\Arduino')
   # checkText('/data1/repositories/work/pulmonai/pulmonai/visualize/nodules/000.nii.gz/screenshots/inf/nod_000_inference_screenshot.png')
    #measurement = get_measurements('/home/arppit/Music/outputs/nodsegs/seg002.nii.gz')
    #test('/data1/repositories/work/pulmonai/outputs/initial/nodbox_492/nod_002.nii.gz', '/data1/repositories/work/pulmonai/outputs/initial/nodsegs_492/seg002.nii.gz', './', measurement)
    # print(os.path.isfile('/home/arppit/Documents/pulmonai/outputs/initial/nodsegs_314_/seg002.nii.gz'))
    # p=get_nodule_3d('/home/arppit/Documents/pulmonai/outputs/initial/nodsegs_463_/seg003.nii.gz')
    # print(p)
    # render_vtp('C:\\Users\\Arppit\\Documents\\Arduino\\noduleSurface.vtp')
    # save_aorta(
    #     'C:\\Users\\Arppit\\Documents\\Arduino\\WHS_lab_vol_CTA.nii.gz')
