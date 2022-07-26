import os
import sys
import vtk
import argparse
import textwrap
from pathlib import Path


class Render:
    def __init__(self, inp, output_f, orientation_cube=False):
        self.output_f = output_f
        self.orientation_cube = orientation_cube
        print(f'### SCRIPT FOR GENERATING THUMBNAIL USING VTK')
        self.filetype = ''
        try:
            if os.path.isfile(inp):
                if inp.split('.')[-1] == 'gz' or inp.split('.')[-1] == 'nii':
                    self.reader = vtk.vtkNIFTIImageReader()
                    self.reader.SetFileName(inp)
                elif inp.split('.')[-1] == 'mhd':
                    self.reader = vtk.vtkMetaImageReader()
                    self.reader.SetFileName(inp)
            else:
                self.reader = vtk.vtkDICOMImageReader()
                self.reader.SetDirectoryName(inp)
            self.reader.Update()
        except Exception as e:
            print(e)
            print('[ERROR] input file/ folder not supported')
            sys.exit()

    def get_otf_heart(self):
        otf = vtk.vtkPiecewiseFunction()
        otf.AddPoint(-2048, 0, 0.5, 0)
        otf.AddPoint(-142.68, 0, 0.5, 0)
        otf.AddPoint(145.2, 0.12, 0.5, 0)
        otf.AddPoint(192.17, 0.56, 0.5, 0)
        otf.AddPoint(217.24, 0.78, 0.5, 0)
        otf.AddPoint(384.35, 0.83, 0.5, 0)
        otf.AddPoint(3661, 0.83, 0.5, 0)
        return otf

    def get_ctf_heart(self):
        ctf = vtk.vtkColorTransferFunction()
        ctf.AddRGBPoint(-2048, 0/255, 0/255, 0)
        ctf.AddRGBPoint(-142.68, 0/255, 0/255, 0)
        ctf.AddRGBPoint(145.2,  157/255, 0/255, 4/255)
        ctf.AddRGBPoint(192.17, 232/255, 116/255, 0/255)
        ctf.AddRGBPoint(217.24, 248/255, 206/255, 116/255)
        ctf.AddRGBPoint(384.35, 232/255, 232/255, 1)
        ctf.AddRGBPoint(3661, 1, 1, 1)
        return ctf

    def get_gtf(self):
        gtf = vtk.vtkPiecewiseFunction()
        gtf.AddPoint(0, 1.00, 0.5, 0.0)
        gtf.AddPoint(255, 1, 0.5, 0)
        return gtf

    def volume_render(self):
        vol = vtk.vtkGPUVolumeRayCastMapper()
        vol.SetInputConnection(self.reader.GetOutputPort())
        # vol.SetMaskTypeToBinary()
        # vol.SetMaskInput(mreader.GetOutput())
        vol.Update()
        volume = vtk.vtkVolume()
        volume.SetMapper(vol)
        otf = self.get_otf_heart()
        volume.GetProperty().SetScalarOpacity(otf)
        # AddPoint (double x, double y, double midpoint, double sharpness)
        ctf = self.get_ctf_heart()
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
        gtf = self.get_gtf()
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
            renderer = self.set_camera_orientation(ren, orientation)
            self.generate_window(renderer, orientation,
                                 self.output_f, self.orientation_cube)
            del renderer

    def save_image(self, window, image_name, temp_dirr, json=False):
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

    def generate_window(self, renderer, orientation, output_file, orientation_cube=True):
        file_name = 'VR_Heart'
        window = vtk.vtkRenderWindow()
        window.SetSize(1024, 1024)
        window.AddRenderer(renderer)
        if orientation_cube:
            interactor = vtk.vtkRenderWindowInteractor()
            interactor.SetRenderWindow(window)
            interactor.Initialize()
            axesActor = self.get_cube_actor_2()
            axes = vtk.vtkOrientationMarkerWidget()
            axes.SetOrientationMarker(axesActor)
            axes.SetInteractor(interactor)
            axes.EnabledOn()
            axes.InteractiveOn()
        window.Render()
        if orientation == 'P':
            # interactor.Start()
            imagedata1 = self.save_image(
                window, f"{file_name}_posterior.png", output_file, json=False)
            print(imagedata1)
        if orientation == 'A':
            imagedata1 = self.save_image(
                window, f"{file_name}_anterior.png", output_file, json=False)
            print(imagedata1)
        if orientation == 'L':
            imagedata1 = self.save_image(
                window, f"{file_name}_left.png", output_file, json=False)
            print(imagedata1)
        if orientation == 'R':
            imagedata1 = self.save_image(
                window, f"{file_name}_right.png", output_file, json=False)
            print(imagedata1)
        if orientation == 'S':
            imagedata1 = self.save_image(
                window, f"{file_name}_superior.png", output_file, json=False)
            print(imagedata1)
        if orientation == 'I':
            imagedata1 = self.save_image(
                window, f"{file_name}_inferior.png", output_file, json=False)
            print(imagedata1)

    def get_cube_actor(self, flip=True):
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

    def get_cube_actor_2(self):
        orientMarkerCubeProp = self.get_cube_actor()
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

    def set_camera_orientation(self, renderer, orientation):
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
            # Camera in Z so it display XY planes.
            camera.SetPosition(0, 0, -1)
            camera.SetViewUp(1, 0, 0)
            renderer.ResetCamera()
            return renderer

    def generate_axial_ss(self, windoWidth=-700, windowLevel=1500):
        (xMin, xMax, yMin, yMax, zMin, zMax) = self.reader.GetExecutive(
        ).GetWholeExtent(self.reader.GetOutputInformation(0))
        (xSpacing, ySpacing, zSpacing) = self.reader.GetOutput().GetSpacing()
        (x0, y0, z0) = self.reader.GetOutput().GetOrigin()

        center = [x0 + xSpacing * 0.5 * (xMin + xMax), y0 + ySpacing * 0.5 *
                  (yMin + yMax), z0 + zSpacing * 0.5 * (zMin + zMax)]

        axial = vtk.vtkMatrix4x4()
        axial.DeepCopy((1, 0, 0, x0,
                        0, 1, 0, y0,
                        0, 0, 1, z0,
                        0, 0, 0, 1))
        reslice = vtk.vtkImageReslice()
        reslice.SetInputConnection(self.reader.GetOutputPort())
        reslice.SetOutputDimensionality(2)
        reslice.SetResliceAxes(axial)

        reslice.SetOutputDimensionality(2)

        reslice.SetInterpolationModeToLinear()
        color = vtk.vtkImageMapToWindowLevelColors()
        color.SetLevel(windoWidth)
        color.SetWindow(windowLevel)
        color.SetInputConnection(reslice.GetOutputPort())
        color.Update()
        # Display the image
        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputConnection(color.GetOutputPort())
        # print(color.GetOutput().GetBounds())
        renderer = vtk.vtkRenderer()
        renderer.AddActor(actor)

        camera = renderer.GetActiveCamera()
        camera.SetFocalPoint(0, 0, 0)

        camera.SetPosition(0, 0, -1)  # Camera in Z so it display XY planes.
        camera.SetViewUp(0, -1, 0)
        renderer.ResetCamera()
        renderer.ResetCameraClippingRange()
        actor = vtk.vtkImageActor()
        actor.GetMapper().SetInputConnection(color.GetOutputPort())
        # print(color.GetOutput().GetBounds())
        renderer = vtk.vtkRenderer()
        renderer.AddActor(actor)

        camera = renderer.GetActiveCamera()
        camera.SetFocalPoint(0, 0, 0)

        camera.SetPosition(0, 0, -1)  # Camera in Z so it display XY planes.
        camera.SetViewUp(0, -1, 0)
        renderer.ResetCamera()
        renderer.ResetCameraClippingRange()
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
        self.save_image(window, 'axial_at_center.png', self.output_f)


# r = Render('C:\\Users\\Arppit\\Documents\\Activision\\dicom\\',
#            'C:\\Users\\Arppit\\Documents\\Activision\\')
# r.volume_render()
# r.generate_axial_ss()

def main():
    data_root = os.path.abspath(__file__)
    parser = argparse.ArgumentParser(
        prog=" Script to generate thumbnails for dicom/nifti/mhd files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
            Description:
                Volume Rendering screenshot, from dicom data. 
                            
            '''),
        epilog=textwrap.dedent('''\

                Usage:
                    1. python thumbnail.py -i /path/to/dicom/dir  -o /path/to/output/folder  -OC False  -r True -ww -700 -wl 1500
                ''')
    )
    parser._action_groups.pop()
    required = parser.add_argument_group('Required Arguments')
    optional = parser.add_argument_group('Optional Arguments')

    required.add_argument('-i', '--input', type=Path,
                          help='folder in which DICOM exists',
                          default=f"{data_root}/inputs/")

    required.add_argument('-o', '--output_f', type=Path,
                          help='folder in which images will be stored',
                          default=f"{data_root}/outputs")

    optional.add_argument('-OC', '--cube', type=bool,
                          help='if orientation cube is needed on each image',
                          default=False)
    optional.add_argument('-r', '--recursive', type=bool,
                          help='if needed to perform on more than one file',
                          default=False)
    optional.add_argument('-ww', '--windowWidth', type=int,
                          help='specify window width',
                          default=-700)
    optional.add_argument('-wl', '--windowLevel', type=int,
                          help='specify windowLevel',
                          default=1500)
    args = parser.parse_args()
    print(args.recursive)
    if args.recursive:
        dirs = os.listdir(args.input)
        n = len(dirs)
        c = 1
        for dir in dirs:
            print(f"{args.input}\\{dir}")
            os.makedirs(f"{args.output_f}\\{dir}")
            render = Render(f"{args.input}\\{dir}",
                            f"{args.output_f}\\{dir}", f"{args.cube}")
            render.volume_render()
            render.generate_axial_ss(args.windowWidth, args.windowLevel)
            print("*"*35 + str(n//c * 100)+'% '+'*'*35)
            c += 1
    else:
        render = Render(str(args.input), str(args.output_f), f"{args.cube}")
        render.volume_render()
        render.generate_axial_ss(args.windowWidth, args.windowLevel)


if __name__ == '__main__':
    main()
