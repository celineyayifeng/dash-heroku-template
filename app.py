import pandas as pd
import numpy as np
import os
import dotenv
import json
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
import requests 
from datetime import date, timedelta
import plotly.io as pio
pio.renderers.default = 'iframe' # or 'notebook' or 'colab'
import dash
from jupyter_dash import JupyterDash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


dotenv.load_dotenv()
covidApp=os.getenv('covidApp')
covidSecretToken=os.getenv('covidSecretToken')
covidID=os.getenv('covidID')
covidSecret=os.getenv('covidSecret')

url = "http://data.virginia.gov/resource/bre9-aqqr.json"

my_pars = {'$limit':100000,
          '$$app_token':covidApp}

headers = {'user-agent': 'Yayi Feng (yf7qq@virginia.edu)'}

r = requests.get(url, params=my_pars, headers=headers)
r

covid = pd.json_normalize(json.loads(r.text))
covid['total_cases'] = covid.total_cases.astype('int')
covid['hospitalizations'] = covid.hospitalizations.astype('int')
covid['deaths'] = covid.deaths.astype('int')

url2 = "http://data.virginia.gov/resource/5s4f-hthh.json"
r2 = requests.get(url2, params=my_pars, headers=headers)
pop = pd.json_normalize(json.loads(r2.text))
pop

pop = pop.query("year=='2019'")
pop

pop['population_estimate'] = pop.population_estimate.astype('int')
pop = pop.groupby('fips').agg({'population_estimate':'sum'}).reset_index()
pop

covidpop = pd.merge(covid, pop, on='fips', validate='many_to_one', indicator="matched")

covidpop.matched.value_counts()

lcl = 'Charlottesville'
changedf = covidpop[covidpop.locality == lcl]
changedf['report_date'] = pd.to_datetime(changedf['report_date'])
changedf.index = changedf['report_date']

#Data from today
now = changedf.loc[str(date.today())]

#Data from yesterday, just in case there's no data today
yesterday = changedf.loc[str(date.today() - timedelta(days=1))]

#Data from 14 days ago
back14 = changedf.loc[str(date.today() - timedelta(days=14))]

back15 = changedf.loc[str(date.today() - timedelta(days=15))]

back28 = changedf.loc[str(date.today() - timedelta(days=28))]


try: 
    newcases = now.total_cases[0] - back14.total_cases[0]
except:
    newcases = yesterday.total_cases[0] - back14.total_cases[0]

prevcases = back14.total_cases[0] - back28.total_cases[0]
changecases = newcases - prevcases
percentchange = round(100*(changecases/prevcases),2)

values = [yesterday.locality[0],
         yesterday.vdh_health_district[0],
         newcases,
         prevcases,
         changecases,
         percentchange]

labels = ['Locality',
         'VDH Health District',
         'New Cases: {} to {}'.format(str(date.today()-timedelta(days=14)),str(date.today())),
         'New Cases: {} to {}'.format(str(date.today()-timedelta(days=28)),str(date.today()-timedelta(days=14))),
         'Total change in new cases',
         'Percent change in new cases']

displaychange = pd.concat([pd.DataFrame(labels), pd.DataFrame(values)], axis=1)
displaychange.columns = ['Local Conditions', '']
displaychange

table = ff.create_table(displaychange)
table.show()

vadf = covidpop.groupby('report_date').agg({'total_cases':'sum',
                                          'hospitalizations':'sum',
                                          'deaths':'sum'}).reset_index()

vadf = pd.melt(vadf, id_vars = 'report_date',
              value_vars = ['total_cases', 'hospitalizations', 'deaths'])
vadf = vadf.rename({'variable':'outcome','value':'count'},axis=1)
vadf

figline = px.line(vadf, x='report_date', y='count', color='outcome', facet_row='outcome',
                 height=600, width=800)
figline.update(layout=dict(title=dict(x=0.5)))
figline.update_yaxes(matches=None)
figline.show()

covidpop

today = covidpop[covidpop.report_date==covidpop.report_date.max()]
today = today[['locality','fips','total_cases','population_estimate']]
today['covid_rate']=today.total_cases/today.population_estimate

today

from urllib.request import urlopen
with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)
    
fig = px.choropleth(today, geojson=counties, locations='fips', color='covid_rate',
                   hover_name='locality',
                   color_continuous_scale="Viridis",
                   scope="usa",
                   labels={"covid_rate":"COVID cases per 100 people"})
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
fig.update_geos(fitbounds="locations", visible=False)
fig.show()

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div(
        [
            html.H1("Virginia COVID Dashboard"),
            html.H5("Author: Celine Feng (yf7qq@virginia.edu)"),
            dcc.Dropdown(id='locality_dropdown',
                        options = [{'label':i, 'value': i} for i in covidpop.locality.unique()],
                        value = 'Charlottesville'),
            dcc.Graph(id='mytable'),
            dcc.Graph(figure=fig),
            dcc.Graph(figure=figline)
        ]
)

@app.callback(
    Output('mytable','figure'),#what element in the app get do we pull output from?, what kind of output),
    Input('locality_dropdown','value')
    #what element in the app provides the input, what kind of input))
    )
#immediately after the callback, write the function that maps inputs to outputs.

def createlocaltable(lcl): 
    changedf = covidpop[covidpop.locality == lcl]
    changedf['report_date'] = pd.to_datetime(changedf['report_date'])
    changedf.index = changedf['report_date']

    #Data from today
    now = changedf.loc[str(date.today())]
    #Data from 14 days ago
    back14 = changedf.loc[str(date.today() - timedelta(days=14))]

    back15 = changedf.loc[str(date.today() - timedelta(days=15))]

    back28 = changedf.loc[str(date.today() - timedelta(days=28))]
    newcases = now.total_cases[0] - back14.total_cases[0]
    prevcases = back14.total_cases[0] - back28.total_cases[0]
    changecases = newcases - prevcases
    percentchange = round(100*(changecases/prevcases),2)

    values = [now.locality[0],
             now.vdh_health_district[0],
             newcases,
             prevcases,
             changecases,
             percentchange]

    labels = ['Locality',
             'VDH Health District',
             'New Cases: {} to {}'.format(str(date.today()-timedelta(days=14)),str(date.today())),
             'New Cases: {} to {}'.format(str(date.today()-timedelta(days=28)),str(date.today()-timedelta(days=14))),
             'Total change in new cases',
             'Percent change in new cases']

    displaychange = pd.concat([pd.DataFrame(labels), pd.DataFrame(values)], axis=1)
    displaychange.columns = ['Local Conditions', '']
    table = ff.create_table(displaychange)
    return table
    
if __name__ == '__main__':
    app.run_server(debug=True)


