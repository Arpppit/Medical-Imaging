import os
import vtk
from loguru import logger
import base64
from glob import glob


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
    imagedata1 = get_b64_image(window, f"{file_name}_{name}_posterior.png", f)
    imagef['A'] = imagedata1
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


print(len(render_image3d("C:\\Users\\Arppit\\Documents\\Arduino\\label.nii.gz",
      "C:\\Users\\Arppit\\Documents\\Arduino", "test")))
