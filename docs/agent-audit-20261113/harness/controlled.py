from pathlib import Path
source=Path(__file__).with_name('diagnostic.py').read_text(encoding='utf8')
source=source.replace('("portfolio-grounded","https://portfolio2-mu-inky.vercel.app/"','("portfolio-fixed-route","https://portfolio2-mu-inky.vercel.app/dial/"')
source=source.replace('active.name=="portfolio-grounded"','active.name=="portfolio-fixed-route"')
source=source.replace('("scribb-supported","https://www.scribb.xyz/","Open Explore and open the Demo Journal."),','')
exec(compile(source,str(Path(__file__).with_name('diagnostic.py')),'exec'))
