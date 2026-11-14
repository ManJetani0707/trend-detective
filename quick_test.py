from src.config import VARIABLES
from src.data import fetch_earthaccess
c = fetch_earthaccess(VARIABLES['merra2_t2m'], (70, 22, 72, 24), 2020, 2021)
print(c.shape, float(c.mean()))