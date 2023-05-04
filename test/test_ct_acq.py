from Lima import Core
import Interface






def main():

    hwint = Interface.Interface()
    ct = Core.CtControl(hwint)
    image = ct.image()
    acq = ct.acquisition()
    saving = ct.saving()
    
    

    
if __name__ == "__main__":
    sys.exit(main())
