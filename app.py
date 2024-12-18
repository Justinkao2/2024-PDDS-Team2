import sqlite3
import pandas as pd
from dash import Dash, html, dcc, Input, Output, ctx
import plotly.graph_objects as go
import plotly.express as px
import plotly.colors as pc
from plotly.subplots import make_subplots 
import itertools
import dash_bootstrap_components as dbc

# Define styles at the top of the file
COLOR_SCHEME = {
    'primary': '#ffb65f',     
    'secondary': '#e6e6e6',   
    'accent': '#ffb65f',      
    'background': '#ffffff',  
    'text': '#333333'         
}

# Card style definition
CARD_STYLE = {
    'backgroundColor': '#ffffff',
    'borderRadius': '15px',
    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
    'padding': '32px',
    'marginBottom': '32px',
    'border': f'1px solid {COLOR_SCHEME["secondary"]}'
}

TEXT_STYLES = {
    'header': {
        'fontSize': '44px',
        'fontWeight': '600',
        'letterSpacing': '1px',
        'color': COLOR_SCHEME['primary'],
        'marginBottom': '8px'
    },
    'subheader': {
        'fontSize': '20px',
        'color': COLOR_SCHEME['secondary'],
        'opacity': '0.9',
        'marginBottom': '4px'
    },
    'section_header': {
        'fontSize': '32px',
        'fontWeight': '600',
        'color': COLOR_SCHEME['primary'],
        'textAlign': 'center',
        'marginBottom': '32px',
        'marginTop': '16px'
    },
    'label': {
        'fontSize': '18px',
        'fontWeight': '500',
        'color': COLOR_SCHEME['text'],
        'marginBottom': '12px',
        'display': 'block'
    }
}

BUTTON_STYLE = {
    'margin': '8px',
    'padding': '12px 24px',
    'backgroundColor': COLOR_SCHEME['primary'],
    'color': '#ffffff',  # White text
    'border': 'none',
    'borderRadius': '30px',
    'cursor': 'pointer',
    'fontWeight': '500',
    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
    'transition': 'all 0.3s ease',
    'textTransform': 'uppercase',
    'letterSpacing': '0.5px',
    ':hover': {
        'backgroundColor': '#e6a14f',
        'boxShadow': '0 4px 8px rgba(0,0,0,0.2)'
    }
}

TAB_STYLE = {
    'borderBottom': '1px solid #d6d6d6',
    'padding': '16px 24px',
    'fontWeight': '600',
    'fontSize': '18px',
    'color': COLOR_SCHEME['text'],
    'backgroundColor': 'white',
    'borderRadius': '15px 15px 0 0',
    'marginRight': '4px',
    'transition': 'all 0.3s ease'
}

TAB_SELECTED_STYLE = {
    'borderTop': f'3px solid {COLOR_SCHEME["primary"]}',
    'borderBottom': '1px solid white',
    'backgroundColor': 'white',
    'color': COLOR_SCHEME['primary'],
    'padding': '16px 24px',
    'fontWeight': '600',
    'fontSize': '18px',
    'borderRadius': '15px 15px 0 0',
    'marginRight': '4px',
    'boxShadow': '2px -2px 4px rgba(0,0,0,0.1)'
}

def get_db_connection():
    """Create and return a database connection"""
    db_path = 'CustomerData.db'
    return sqlite3.connect(db_path)

def load_transaction_data():
    """Load and return base transaction data"""
    conn = get_db_connection()
    base_query = """
    SELECT 
        td.Transaction_ID,
        td.Student_id,
        td.Order_Date,
        sb.Age AS Customer_Age,
        sb.Gender AS Customer_Gender,
        sla.City AS City,
        sla.[Learning Area] AS Region,
        ct.Course_Type_Name,
        td.Transaction_Value AS Amount
    FROM transaction_data td
    LEFT JOIN student_basic sb ON td.Student_id = sb.StudentID
    LEFT JOIN student_learning_area sla ON td.Student_id = sla.StudentID
    LEFT JOIN course_data cd ON td.Student_id = cd.Student_id
    LEFT JOIN course_type ct ON cd.Course_Type_id = ct.Course_Type_ID
    """
    df = pd.read_sql_query(base_query, conn)
    conn.close()
    df['Order_Date'] = pd.to_datetime(df['Order_Date'])
    return df

def load_data_BT():
    """Load data for Business Trends"""
    df = load_transaction_data()
    df['Day_of_Week'] = df['Order_Date'].dt.day_name()
    df['Month'] = df['Order_Date'].dt.month_name()
    return df

def load_data_MR():
    """Load data for Monthly Revenue"""
    df = load_transaction_data()
    df['Month_Year'] = df['Order_Date'].dt.to_period('M').astype(str)
    monthly_revenue = df.groupby('Month_Year')['Amount'].sum().reset_index()
    monthly_revenue['Growth_Rate'] = monthly_revenue['Amount'].pct_change() * 100
    return monthly_revenue

def load_data_DA():
    """Load data for Demographic Analysis"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify if tables exist
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name IN ('student_basic', 'student_learning_area', 
                                      'student_learning_type', 'course_student')
    """)
    existing_tables = cursor.fetchall()
    existing_tables = [table[0] for table in existing_tables]
    
    required_tables = ['student_basic', 'student_learning_area', 
                      'student_learning_type', 'course_student']
    
    missing_tables = set(required_tables) - set(existing_tables)
    if missing_tables:
        raise Exception(f"Missing tables in database: {missing_tables}")

    # SQL query to combine relevant data
    query = """
    SELECT 
        sb.StudentID,
        sb.Age,
        sb.Gender,
        sla.City,
        sla.[Learning Area],
        cs.Course_Type_id
    FROM 
        student_basic sb
    LEFT JOIN 
        student_learning_area sla ON sb.StudentID = sla.StudentID
    LEFT JOIN 
        student_learning_type slt ON sb.StudentID = slt.StudentID
    LEFT JOIN 
        course_student cs ON sb.StudentID = cs.Student_id;
    """

    # Execute query and load into dataframe
    DA_data = pd.read_sql_query(query, conn)
    conn.close()
    
    # Validate data
    if DA_data.empty:
        raise Exception("No data was retrieved from the database")
    
    # Define course type mapping
    course_data = pd.DataFrame({
        "Course_Type_id": [1, 2, 3],
        "Course_Type_Name": ["瑜珈", "律動", "舞蹈"],
        "Course_Type_Note": ["Yoga Classes", "Rhythmic Movement Classes", "Dance Classes"]
    })

    # Merge course data
    DA_data = DA_data.merge(course_data, on="Course_Type_id", how="left")

    # Clean data
    DA_data['Gender'] = DA_data['Gender'].fillna('Unknown')
    DA_data['Learning Area'] = DA_data['Learning Area'].fillna('Unknown')
    DA_data['Course_Type_id'] = DA_data['Course_Type_id'].fillna('Unknown')

    return DA_data

def load_data_TP():
    """Fetch teacher performance data from the database"""
    conn = get_db_connection()
    query = """
        SELECT 
            tb.TeacherID AS Teacher_ID,
            tb.FirstName || ' ' || tb.LastName AS Teacher_Name,
            sb.StudentID AS Student_ID,
            sb.Gender AS Student_Gender,
            sb.Age AS Student_Age,
            sla.City AS Learning_City,
            sla.[Learning Area] AS Learning_Area,
            ch.Course_Date
        FROM course_history ch
        LEFT JOIN teacher_basic tb ON ch.Teacher_id = tb.TeacherID
        LEFT JOIN course_student cs ON ch.Course_id = cs.Course_id
        LEFT JOIN course_basic cb ON cs.Course_Type_id = cb.Course_Type_id
        LEFT JOIN student_learning_area sla ON cs.Student_id = sla.StudentID
        LEFT JOIN student_basic sb ON cs.Student_id = sb.StudentID
        ORDER BY ch.Teacher_id
    """
    
    try:
        TP_Data = pd.read_sql_query(query, conn)
        
        if not TP_Data.empty:
            # Ensure columns are in the correct order
            column_order = [
                'Teacher_ID',
                'Teacher_Name',
                'Student_ID',
                'Student_Gender',
                'Student_Age',
                'Learning_City',
                'Learning_Area',
                'Course_Date'
            ]
            
            # Reorder columns and fill any missing values
            TP_Data = TP_Data.reindex(columns=column_order)
            TP_Data = TP_Data.fillna({
                'Teacher_Name': 'Unknown',
                'Student_Gender': 'Unknown', 
                'Learning_Area': 'Unknown'
            })
            
            # Calculate metrics
            TP_Data['Course_Date'] = pd.to_datetime(TP_Data['Course_Date'])
            
            
            # Calculate years of experience based on first course date
            TP_Data['First_Course'] = TP_Data.groupby('Teacher_ID')['Course_Date'].transform('min')
            TP_Data = TP_Data.drop('First_Course', axis=1)
            
            return TP_Data
            
    except Exception as e:
        print(f"Error in load_data_TP: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

    return pd.DataFrame()

# Load data first
BT_data = load_data_BT()
MR_data = load_data_MR()
DA_data = load_data_DA()
TP_data = load_data_TP()
base_data = load_transaction_data()

# Check if TP_data loaded successfully
if TP_data.empty:
    print("Warning: Teacher performance data is empty")
else:
    #print(f"Successfully loaded teacher performance data:")
    
    try:
        if 'Total_Teaching_Hours' in TP_data.columns:
            print(f"- Total teaching hours: {TP_data['Total_Teaching_Hours'].sum():,.0f}")
        if 'Total_Revenue' in TP_data.columns:
            print(f"- Total sales revenue: ${TP_data['Total_Revenue'].sum():,.2f}")
        if 'Years_of_Experience' in TP_data.columns:
            print(f"- Average years of experience: {TP_data['Years_of_Experience'].mean():.1f}")
    except Exception as e:
        print(f"Warning: Some metrics couldn't be calculated - {str(e)}")



# Initialize the Dash app
app = Dash(__name__)

server = app.server

CHART_THEME = 'plotly_dark'

# Update the layout with new text styles
app.layout = html.Div([
    # Header section (stays outside tabs)
    html.Div([
        html.Div([
            html.H1("Innodanc Dashboard", 
                    style=TEXT_STYLES['header']),
            html.Div([
                html.P("Developed by Team No.2 Magpies", 
                       style={'color': COLOR_SCHEME['text'], 'fontSize': '28px', 'marginBottom': '8px'}),
                html.P("周芸瑄 • 楊誼萱 • 高愷傑 • 林樂瑞", 
                       style={'color': COLOR_SCHEME['text'], 'fontSize': '24px', 'opacity': '0.9'})
            ], style={'marginTop': '12px'})
        ], style={'textAlign': 'center'})
    ], style={
        'background': '#ffffff',
        'marginBottom': '32px',
        'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
        'padding': '24px',
        'border': f'1px solid {COLOR_SCHEME["secondary"]}'
    }),
    
    # Tabs
    dcc.Tabs(
        id='tabs',
        value='glimpse',
        children=[
            dcc.Tab(
                label='Glimpse',
                value='glimpse',
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=[
                    html.Div([
                        html.H2("Overview Dashboard", style=TEXT_STYLES['section_header']),
                        
                        # Key Metrics Row
                        html.Div([
                            # Total Revenue Card
                            html.Div([
                                html.H3("Total Revenue", style={
                                    'fontSize': '20px',
                                    'color': COLOR_SCHEME['text'],
                                    'marginBottom': '8px'
                                }),
                                html.H4(
                                    f"${base_data['Amount'].sum():,.2f}", 
                                    style={
                                        'fontSize': '32px',
                                        'color': COLOR_SCHEME['primary'],
                                        'marginTop': '0'
                                    }
                                )
                            ], style={**CARD_STYLE, 'flex': '1', 'textAlign': 'center'}),
                            
                            # Total Students Card
                            html.Div([
                                html.H3("Total Students", style={
                                    'fontSize': '20px',
                                    'color': COLOR_SCHEME['text'],
                                    'marginBottom': '8px'
                                }),
                                html.H4(
                                    f"{base_data['Student_id'].nunique():,}", 
                                    style={
                                        'fontSize': '32px',
                                        'color': COLOR_SCHEME['primary'],
                                        'marginTop': '0'
                                    }
                                )
                            ], style={**CARD_STYLE, 'flex': '1', 'textAlign': 'center'}),
                            
                            # Total Teachers Card
                            html.Div([
                                html.H3("Total Teachers", style={
                                    'fontSize': '20px',
                                    'color': COLOR_SCHEME['text'],
                                    'marginBottom': '8px'
                                }),
                                html.H4(
                                    f"{TP_data['Teacher_ID'].nunique():,}", 
                                    style={
                                        'fontSize': '32px',
                                        'color': COLOR_SCHEME['primary'],
                                        'marginTop': '0'
                                    }
                                )
                            ], style={**CARD_STYLE, 'flex': '1', 'textAlign': 'center'}),
                            
                            # Average Transaction Value Card
                            html.Div([
                                html.H3("Avg Transaction Value", style={
                                    'fontSize': '20px',
                                    'color': COLOR_SCHEME['text'],
                                    'marginBottom': '8px'
                                }),
                                html.H4(
                                    f"${base_data['Amount'].mean():,.2f}", 
                                    style={
                                        'fontSize': '32px',
                                        'color': COLOR_SCHEME['primary'],
                                        'marginTop': '0'
                                    }
                                )
                            ], style={**CARD_STYLE, 'flex': '1', 'textAlign': 'center'})
                        ], style={'display': 'flex', 'gap': '24px', 'marginBottom': '24px'}),
                        
                        # Charts Row
                        html.Div([
                            # Revenue Trend
                            html.Div([
                                dcc.Graph(id='overview-revenue-trend')
                            ], style={**CARD_STYLE, 'flex': '1'}),
                            
                            # Course Distribution
                            html.Div([
                                dcc.Graph(id='overview-course-dist')
                            ], style={**CARD_STYLE, 'flex': '1'})
                        ], style={'display': 'flex', 'gap': '24px', 'marginBottom': '24px'}),
                        
                        # Bottom Charts Row
                        html.Div([
                            # Gender Distribution
                            html.Div([
                                dcc.Graph(id='overview-gender-dist')
                            ], style={**CARD_STYLE, 'flex': '1'}),
                            
                            # Age Distribution
                            html.Div([
                                dcc.Graph(id='overview-age-dist')
                            ], style={**CARD_STYLE, 'flex': '1'})
                        ], style={'display': 'flex', 'gap': '24px'})
                    ], id='glimpse-content', style={'padding': '24px'})     
                ]
            ),
            
            # Overview Tab (existing)
            dcc.Tab(
                label='Overview',
                value='overview',
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=[
                    html.Div([
                        # Filters section
                        html.Div([
                            html.Div([
                                html.Label("Date Range", style=TEXT_STYLES['label']),
                                dcc.DatePickerRange(
                                    id='date-range-combined',
                                    start_date=base_data['Order_Date'].min(),
                                    end_date=base_data['Order_Date'].max(),
                                    display_format='YYYY-MM-DD',
                                    style={'zIndex': 1000, 'fontSize': '16px'}
                                )
                            ], style={'flex': '1', 'marginRight': '32px'}),
                            
                            html.Div([
                                html.Label("Age Range", style=TEXT_STYLES['label']),
                                dcc.RangeSlider(
                                    id='age-range-demo',
                                    min=DA_data['Age'].min(),
                                    max=DA_data['Age'].max(),
                                    step=1,
                                    marks={i: {'label': str(i), 'style': {'color': COLOR_SCHEME['text'], 'fontSize': '14px'}} 
                                           for i in range(int(DA_data['Age'].min()), int(DA_data['Age'].max()) + 1, 5)},
                                    value=[DA_data['Age'].min(), DA_data['Age'].max()]
                                )
                            ], style={'flex': '1', 'marginRight': '24px'}),
                            
                            html.Div([
                                html.Label("Course Type", style=TEXT_STYLES['label']),
                                dcc.Dropdown(
                                    id='course-type-combined',
                                    options=[{'label': course, 'value': course} 
                                           for course in base_data['Course_Type_Name'].unique()],
                                    multi=True,
                                    style={'borderRadius': '8px', 'fontSize': '28px'}
                                )
                            ], style={'flex': '1', 'marginRight': '24px'}),
                            
                            html.Div([
                                html.Label("City", style=TEXT_STYLES['label']),
                                dcc.Dropdown(
                                    id='region-revenue',
                                    options=[{'label': City, 'value': City} 
                                           for City in DA_data['City'].unique()],
                                    multi=True,
                                    style={'borderRadius': '8px', 'fontSize': '28px'}
                                )
                            ], style={'flex': '1', 'marginRight': '24px'}),
                            
                            html.Div([
                                html.Label("Gender", style=TEXT_STYLES['label']),
                                dcc.Dropdown(
                                    id='gender-dropdown',
                                    options=[{'label': gender, 'value': gender} 
                                           for gender in base_data['Customer_Gender'].unique()],
                                    multi=True,
                                    style={'borderRadius': '8px', 'fontSize': '28px'}
                                ),
                            ], style={'flex': '1'})
                        ], style={**CARD_STYLE, 'display': 'flex', 'alignItems': 'flex-end', 'gap': '24px'}),
                        # Revenue & Booking Analysis Section
                        html.Div([
                            html.H2("Revenue & Booking Analysis", style=TEXT_STYLES['section_header']),
                            html.Div([
                                html.Div([
                                    dcc.Graph(
                                        id='monthly-revenue-chart', 
                                        style={'width': '100%', 'height': '600px'}
                                    ),
                                    html.Span(
                                        "ⓘ",  # Info icon
                                        id="info-icon-monthly-revenue-chart",
                                        style={
                                            "fontSize": "20px",
                                            "cursor": "pointer",
                                            "color": "#007BFF",
                                            "position": "relative",
                                            "top": "-50px",
                                            "left": "10px"
                                        }
                                    ),
                                    dbc.Tooltip(
                                        [
                                            html.Ul([
                                                html.Li("Users: Operating Officers, Finance Team"),
                                                html.Li("Purpose: Monitor revenue and growth trends to guide resource allocation and planning."),
                                                html.Li("Chart: Combination (Bar + Line)"),
                                                html.Ul([
                                                    html.Li("Bar Chart: X = Months, Y = Monthly Revenue"),
                                                    html.Li("Line Chart: Y = Growth Rate (%)")
                                                ]),
                                                html.Li("Insights:"),
                                                html.Ul([
                                                    html.Li("Identify peak revenue months and contributing factors."),
                                                    html.Li("Track trends in revenue growth or decline."),
                                                    html.Li("Assess effectiveness of campaigns and seasonal strategies.")
                                                ])
                                            ])
                                        ],
                                        target="info-icon-monthly-revenue-chart",
                                        placement="right",
                                        style={"fontSize": "14px"}
                                    )
                                ], style={"position": "relative", "width": "48%", "display": "inline-block", "marginRight": "2%"}),
                                html.Div([
                                    dcc.Graph(
                                        id='booking-heatmap', 
                                        style={'width': '100%', 'height': '600px'}
                                    ),
                                    html.Span(
                                        "ⓘ",  # Info icon
                                        id="info-icon-booking-heatmap",
                                        style={
                                            "fontSize": "20px",
                                            "cursor": "pointer",
                                            "color": "#007BFF",
                                            "position": "relative",
                                            "top": "-50px",
                                            "left": "10px"
                                        }
                                    ),
                                    dbc.Tooltip(
                                        [
                                            html.Ul([
                                                html.Li("Users: Marketing, Customer Support Teams"),
                                                html.Li("Purpose: Analyze student order patterns over time."),
                                                html.Li("Chart: Heatmap"),
                                                html.Ul([
                                                    html.Li("X-Axis: Months (January to December)."),
                                                    html.Li("Y-Axis: Days of the week (Monday to Sunday)."),
                                                    html.Li("Color Scale: Represents the volume of orders placed.")
                                                ]),
                                                html.Li("Insights:"),
                                                html.Ul([
                                                    html.Li("Detect peak days and months for student purchases."),
                                                    html.Li("Align marketing efforts and promotions with high-order periods."),
                                                    html.Li("Adjust operational resources to cater to peak demand times, ensuring seamless service.")
                                                ])
                                            ])
                                        ],
                                        target="info-icon-booking-heatmap",
                                        placement="right",
                                        style={"fontSize": "14px"}
                                    )

                                ], style={"position": "relative", "width": "48%", "display": "inline-block", "marginLeft": "2%"})
                            ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'width': '100%'})
                        ], style=CARD_STYLE),

                        # Teacher Performance Analysis Section
                        html.Div([
                            html.H2("Teacher Performance Analysis", style=TEXT_STYLES['section_header']),
                            html.Div([
                                html.Div([
                                    dcc.Graph(
                                        id='teacher-class-trend', 
                                        style={'width': '100%', 'height': '600px'}
                                    ),
                                    html.Span(
                                        "ⓘ",  # Info icon
                                        id="info-icon-teacher-class-trend",
                                        style={
                                            "fontSize": "20px",
                                            "cursor": "pointer",
                                            "color": "#007BFF",
                                            "position": "relative",
                                            "top": "-50px",
                                            "left": "10px"
                                        }
                                    ),
                                    dbc.Tooltip(
                                        [
                                        html.Ul([
                                            html.Li("Users: Operating Officers, Finance Team"),
                                            html.Li("Purpose: Analyze top 5 teachers' sales and monthly distribution for better planning."),
                                            html.Li("Chart: Stacked Bar (X: Teacher names, Y: Courses sold, Monthly data)"),
                                            html.Li("Insights:"),
                                            html.Ul([
                                                html.Li("Highlight top-performing teachers."),
                                                html.Li("Understand sales seasonality."),
                                                html.Li("Identify areas for support or incentives.")
                                            ])
                                        ])
                                        ],
                                        target="info-icon-teacher-class-trend",
                                        placement="right",
                                        style={"fontSize": "14px"}
                                    )
                                ], style={"position": "relative", "width": "48%", "display": "inline-block", "marginRight": "2%"}),
                                html.Div([
                                    dcc.Graph(
                                        id='teacher-student-heatmap', 
                                        style={'width': '100%', 'height': '600px'}
                                    ),
                                    html.Span(
                                        "ⓘ",  # Info icon
                                        id="info-icon-teacher-student-heatmap",
                                        style={
                                            "fontSize": "20px",
                                            "cursor": "pointer",
                                            "color": "#007BFF",
                                            "position": "relative",
                                            "top": "-50px",
                                            "left": "10px"
                                        }
                                    ),
                                    dbc.Tooltip(
                                        [
                                            html.Ul([
                                                html.Li("Users: Marketing, Customer Support Teams"),
                                                html.Li("Purpose: Analyze age distribution of students for top 5 teachers."),
                                                html.Li("Chart: Heatmap"),
                                                html.Ul([
                                                    html.Li("X-Axis: Age groups (0-20, 21-30, 31-40, 41-50, 50+)"),
                                                    html.Li("Y-Axis: Top 5 teachers"),
                                                    html.Li("Color Scale: Unique students per age group")
                                                ]),
                                                html.Li("Insights:"),
                                                html.Ul([
                                                    html.Li("Identify primary audience age groups for each teacher."),
                                                    html.Li("Highlight underserved age demographics."),
                                                    html.Li("Support tailored course design and learning experiences.")
                                                ])
                                            ])
                                        ],
                                        target="info-icon-teacher-student-heatmap",
                                        placement="right",
                                        style={"fontSize": "14px"}
                                    ),                                   
                                ], style={"position": "relative", "width": "48%", "display": "inline-block", "marginLeft": "2%"})
                            ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'width': '100%'})
                        ], style=CARD_STYLE),

                        # Student Demographic Analysis Section
                        html.Div([
                            html.H2("Student Demographic Analysis", style=TEXT_STYLES['section_header']),
                            html.Div([
                                html.Button('Gender Distribution', id='btn-gender', n_clicks=0, style=BUTTON_STYLE),
                                html.Button('Age Distribution', id='btn-age', n_clicks=0, style=BUTTON_STYLE),
                                html.Button('Course Distribution', id='btn-course', n_clicks=0, style=BUTTON_STYLE),
                                html.Button('Region Distribution', id='btn-region', n_clicks=0, style=BUTTON_STYLE),
                                html.Button('Age by Course Type', id='btn-age-course', n_clicks=0, style=BUTTON_STYLE)
                            ], style={'textAlign': 'center', 'marginBottom': '24px'}),
                            html.Div([
                                html.Div([
                                    dcc.Graph(
                                        id='demographics-chart', 
                                        style={'width': '100%', 'height': '600px'}
                                    ),
                                    html.Span(
                                        "ⓘ",  # Info icon
                                        id="info-icon-demographics-chart",
                                        style={
                                            "fontSize": "20px",
                                            "cursor": "pointer",
                                            "color": "#007BFF",
                                            "position": "left",
                                            "top": "-50px",
                                            "left": "-10px"
                                        }
                                    ),
                                    dbc.Tooltip(
                                        [
                                            html.Ul([
                                                html.Li("Users: Marketing, Customer Support Teams"),
                                                html.Li("Purpose: Understand student demographics (gender, age, region) for personalized service and growth."),
                                                html.Li("Chart Details:"),
                                                html.Ul([
                                                    html.Li("Pie Chart: Gender distribution (Male, Female)"),
                                                    html.Li("Histogram: X = Age groups, Y = Number of students"),
                                                    html.Li("Bar Chart: X = Geographic regions, Y = Students per region"),
                                                    html.Li("Interactive: Demographic filters with buttons")
                                                ]),
                                                html.Li("Insights:"),
                                                html.Ul([
                                                    html.Li("Understand gender and age composition for marketing and course customization."),
                                                    html.Li("Identify regions with high/low student participation."),
                                                    html.Li("Support regional and demographic-specific outreach.")
                                                ])
                                            ])
                                        ],
                                        target="info-icon-demographics-chart",
                                        placement="right",
                                        style={"fontSize": "14px"}
                                    ),
                                ], style={"position": "relative", "width": "100%", "display": "inline-block"})
                            ], style={'textAlign': 'left', 'marginBottom': '24px'})
                        ], style=CARD_STYLE)
                    ], id='overview-content')
                ]
            ),     
            # Operation & Finance Tab (existing)
            dcc.Tab(
                label='Operation & Finance',
                value='operation',
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=[
                    html.Div([
                        # ... existing operation content ...
                        # Filters section
                        html.Div([
                            html.Div([
                                html.Label("Date Range", style=TEXT_STYLES['label']),
                                dcc.DatePickerRange(
                                    id='operation-date-range-combined',
                                    start_date=base_data['Order_Date'].min(),
                                    end_date=base_data['Order_Date'].max(),
                                    display_format='YYYY-MM-DD',
                                    style={'zIndex': 1000, 'fontSize': '16px'}
                                )
                            ], style={'flex': '1', 'marginRight': '32px'}),
                            
                            html.Div([
                                html.Label("Age Range", style=TEXT_STYLES['label']),
                                dcc.RangeSlider(
                                    id='operation-age-range-demo',
                                    min=DA_data['Age'].min(),
                                    max=DA_data['Age'].max(),
                                    step=1,
                                    marks={i: {'label': str(i), 'style': {'color': COLOR_SCHEME['text'], 'fontSize': '14px'}} 
                                           for i in range(int(DA_data['Age'].min()), int(DA_data['Age'].max()) + 1, 5)},
                                    value=[DA_data['Age'].min(), DA_data['Age'].max()]
                                )
                            ], style={'flex': '1', 'marginRight': '24px'}),
                            
                            html.Div([
                                html.Label("Course Type", style=TEXT_STYLES['label']),
                                dcc.Dropdown(
                                    id='operation-course-type-combined',
                                    options=[{'label': course, 'value': course} 
                                           for course in base_data['Course_Type_Name'].unique()],
                                    multi=True,
                                    style={'borderRadius': '8px', 'fontSize': '28px'}
                                )
                            ], style={'flex': '1', 'marginRight': '24px'}),
                            
                            html.Div([
                                html.Label("City", style=TEXT_STYLES['label']),
                                dcc.Dropdown(
                                    id='operation-region-revenue',
                                    options=[{'label': City, 'value': City} 
                                           for City in DA_data['City'].unique()],
                                    multi=True,
                                    style={'borderRadius': '8px', 'fontSize': '28px'}
                                )
                            ], style={'flex': '1', 'marginRight': '24px'}),
                            
                            html.Div([
                                html.Label("Gender", style=TEXT_STYLES['label']),
                                dcc.Dropdown(
                                    id='operation-gender-dropdown',
                                    options=[{'label': gender, 'value': gender} 
                                           for gender in base_data['Customer_Gender'].unique()],
                                    multi=True,
                                    style={'borderRadius': '8px', 'fontSize': '28px'}
                                ),
                            ], style={'flex': '1'})
                        ], style={**CARD_STYLE, 'display': 'flex', 'alignItems': 'flex-end', 'gap': '24px'}),
                        
                        # Revenue & Booking Analysis Section
                        html.Div([
                            html.H2("Revenue & Booking Analysis", style=TEXT_STYLES['section_header']),
                                html.Div([
                                    dcc.Graph(
                                        id='operation-monthly-revenue-chart',
                                        style={'width': '100%', 'height': '600px'}
                                    ),
                                    html.Span(
                                        "ⓘ",  # Info icon
                                        id="info-icon-operation-monthly-revenue-chart",
                                        style={
                                            "fontSize": "20px",
                                            "cursor": "pointer",
                                            "color": "#007BFF",
                                            "position": "relative",  # 相對定位
                                            "top": "-50px",          # 微調位置
                                            "left": "10px"
                                        }
                                    ),
                                    dbc.Tooltip(
                                        [
                                            html.Ul([
                                                html.Li("Users: Operating Officers, Finance Team"),
                                                html.Li("Purpose: Monitor revenue and growth trends to guide resource allocation and planning."),
                                                html.Li("Chart: Combination (Bar + Line)"),
                                                html.Ul([
                                                    html.Li("Bar Chart: X = Months, Y = Monthly Revenue"),
                                                    html.Li("Line Chart: Y = Growth Rate (%)")
                                                ]),
                                                html.Li("Insights:"),
                                                html.Ul([
                                                    html.Li("Identify peak revenue months and contributing factors."),
                                                    html.Li("Track trends in revenue growth or decline."),
                                                    html.Li("Assess effectiveness of campaigns and seasonal strategies.")
                                                ])
                                            ])
                                        ],
                                        target="info-icon-operation-monthly-revenue-chart",
                                        placement="right",
                                        style={"fontSize": "14px"}
                                    )
 
                                 ], style={"position": "relative", "width": "48%", "display": "inline-block", "marginRight": "2%"}),
                                html.Div([
                                    dcc.Graph(
                                        id='operation-teacher-class-trend', 
                                        style={'width': '100%', 'display': 'inline-block', 'marginRight': '2%'}
                                    ),
                                    html.Span(
                                        "ⓘ",  # Info icon
                                        id="info-icon-operation-teacher-class-trend",
                                        style={
                                            "fontSize": "20px",
                                            "cursor": "pointer",
                                            "color": "#007BFF",
                                            "position": "relative",  # 相對定位
                                            "top": "-50px",          # 微調位置
                                            "left": "10px"
                                        }
                                    ),
                                    dbc.Tooltip(
                                    [
                                        html.Ul([
                                            html.Li("Users: Operating Officers, Finance Team"),
                                            html.Li("Purpose: Analyze top 5 teachers' sales and monthly distribution for better planning."),
                                            html.Li("Chart: Stacked Bar (X: Teacher names, Y: Courses sold, Monthly data)"),
                                            html.Li("Insights:"),
                                            html.Ul([
                                                html.Li("Highlight top-performing teachers."),
                                                html.Li("Understand sales seasonality."),
                                                html.Li("Identify areas for support or incentives.")
                                            ])
                                        ])
                                    ],
                                    target="info-icon-operation-teacher-class-trend",
                                    placement="right",
                                    style={"fontSize": "14px"}
                                )
                                ], style={"position": "relative", "width": "48%", "display": "inline-block", "marginLeft": "2%"})
                        ], style=CARD_STYLE),
                    ], id='operation-content', style={'display': 'none'})
                ]
            ),
            # marketing and customer support tab
            dcc.Tab(
                label='Marketing and Customer Support',
                value='marketing',
                style=TAB_STYLE,
                selected_style=TAB_SELECTED_STYLE,
                children=[
                    html.Div([
                        # ... existing operation content ...
                        # Filters section
                        html.Div([
                            html.Div([
                                html.Label("Date Range", style=TEXT_STYLES['label']),
                                dcc.DatePickerRange(
                                    id='marketing-date-range-combined',
                                    start_date=base_data['Order_Date'].min(),
                                    end_date=base_data['Order_Date'].max(),
                                    display_format='YYYY-MM-DD',
                                    style={'zIndex': 1000, 'fontSize': '16px'}
                                )
                            ], style={'flex': '1', 'marginRight': '32px'}),
                            
                            html.Div([
                                html.Label("Age Range", style=TEXT_STYLES['label']),
                                dcc.RangeSlider(
                                    id='marketing-age-range-demo',
                                    min=DA_data['Age'].min(),
                                    max=DA_data['Age'].max(),
                                    step=1,
                                    marks={i: {'label': str(i), 'style': {'color': COLOR_SCHEME['text'], 'fontSize': '14px'}} 
                                           for i in range(int(DA_data['Age'].min()), int(DA_data['Age'].max()) + 1, 5)},
                                    value=[DA_data['Age'].min(), DA_data['Age'].max()]
                                )
                            ], style={'flex': '1', 'marginRight': '24px'}),
                            
                            html.Div([
                                html.Label("Course Type", style=TEXT_STYLES['label']),
                                dcc.Dropdown(
                                    id='marketing-course-type-combined',
                                    options=[{'label': course, 'value': course} 
                                           for course in base_data['Course_Type_Name'].unique()],
                                    multi=True,
                                    style={'borderRadius': '8px', 'fontSize': '28px'}
                                )
                            ], style={'flex': '1', 'marginRight': '24px'}),
                            
                            html.Div([
                                html.Label("City", style=TEXT_STYLES['label']),
                                dcc.Dropdown(
                                    id='marketing-region-revenue',
                                    options=[{'label': City, 'value': City} 
                                           for City in DA_data['City'].unique()],
                                    multi=True,
                                    style={'borderRadius': '8px', 'fontSize': '28px'}
                                )
                            ], style={'flex': '1', 'marginRight': '24px'}),
                            
                            html.Div([
                                html.Label("Gender", style=TEXT_STYLES['label']),
                                dcc.Dropdown(
                                    id='marketing-gender-dropdown',
                                    options=[{'label': gender, 'value': gender} 
                                           for gender in base_data['Customer_Gender'].unique()],
                                    multi=True,
                                    style={'borderRadius': '8px', 'fontSize': '28px'}
                                ),
                            ], style={'flex': '1'})
                        ], style={**CARD_STYLE, 'display': 'flex', 'alignItems': 'flex-end', 'gap': '24px'}),
                        
                        # Student Booking Time and Recommend Teacher Analysis
                        html.Div([
                            html.H2(
                                "Student Booking Time and Recommend Teacher Analysis", 
                                style=TEXT_STYLES['section_header']
                            ),
                            html.Div([
                                html.Div([
                                    dcc.Graph(
                                        id='marketing-booking-heatmap', 
                                        style={'width': '100%', 'height': '600px'}
                                    ),
                                    html.Span(
                                        "ⓘ",  # Info icon
                                        id="info-icon-marketing-booking-heatmap",
                                        style={
                                            "fontSize": "20px",
                                            "cursor": "pointer",
                                            "color": "#007BFF",
                                            "position": "relative",  # 相對定位
                                            "top": "-50px",          # 微調位置
                                            "left": "10px"
                                        }
                                    ),
                                    dbc.Tooltip(
                                        [
                                            html.Ul([
                                                html.Li("Users: Marketing, Customer Support Teams"),
                                                html.Li("Purpose: Analyze student order patterns over time."),
                                                html.Li("Chart: Heatmap"),
                                                html.Ul([
                                                    html.Li("X-Axis: Months (January to December)."),
                                                    html.Li("Y-Axis: Days of the week (Monday to Sunday)."),
                                                    html.Li("Color Scale: Represents the volume of orders placed.")
                                                ]),
                                                html.Li("Insights:"),
                                                html.Ul([
                                                    html.Li("Detect peak days and months for student purchases."),
                                                    html.Li("Align marketing efforts and promotions with high-order periods."),
                                                    html.Li("Adjust operational resources to cater to peak demand times, ensuring seamless service.")
                                                ])
                                            ])
                                        ],
                                        target="info-icon-marketing-booking-heatmap",
                                        placement="right",
                                        style={"fontSize": "14px"}
                                    )
                                ], style={"position": "relative", "width": "48%", "display": "inline-block", "marginRight": "2%"}),

                                html.Div([
                                    dcc.Graph(
                                        id='marketing-teacher-student-heatmap', 
                                        style={'width': '100%', 'height': '600px'}
                                    ),
                                    html.Span(
                                        "ⓘ",  # Info icon
                                        id="info-icon-marketing-teacher-student-heatmap",
                                        style={
                                            "fontSize": "20px",
                                            "cursor": "pointer",
                                            "color": "#007BFF",
                                            "position": "relative",  # 相對定位
                                            "top": "-50px",          # 微調位置
                                            "left": "10px"
                                        }
                                    ),
                                    dbc.Tooltip(
                                        [
                                            html.Ul([
                                                html.Li("Users: Marketing, Customer Support Teams"),
                                                html.Li("Purpose: Analyze age distribution of students for top 5 teachers."),
                                                html.Li("Chart: Heatmap"),
                                                html.Ul([
                                                    html.Li("X-Axis: Age groups (0-20, 21-30, 31-40, 41-50, 50+)"),
                                                    html.Li("Y-Axis: Top 5 teachers"),
                                                    html.Li("Color Scale: Unique students per age group")
                                                ]),
                                                html.Li("Insights:"),
                                                html.Ul([
                                                    html.Li("Identify primary audience age groups for each teacher."),
                                                    html.Li("Highlight underserved age demographics."),
                                                    html.Li("Support tailored course design and learning experiences.")
                                                ])
                                            ])
                                        ],
                                        target="info-icon-marketing-teacher-student-heatmap",
                                        placement="right",
                                        style={"fontSize": "14px"}
                                    ),                                   
                                ], style={"position": "relative", "width": "48%", "display": "inline-block", "marginRight": "2%"}),
                            ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'width': '100%'})
                        ], style=CARD_STYLE),
                        
                        # Demographics Section (now after Teacher Performance)
                        html.Div([
                            html.H2("Student Demographic Analysis", 
                                    style=TEXT_STYLES['section_header']),
                            html.Div([
                                html.Button('Gender Distribution', id='marketing-btn-gender', n_clicks=0, style=BUTTON_STYLE),
                                html.Button('Age Distribution', id='marketing-btn-age', n_clicks=0, style=BUTTON_STYLE),
                                html.Button('Course Distribution', id='marketing-btn-course', n_clicks=0, style=BUTTON_STYLE),
                                html.Button('Region Distribution', id='marketing-btn-region', n_clicks=0, style=BUTTON_STYLE),
                                html.Button('Age by Course Type', id='marketing-btn-age-course', n_clicks=0, style=BUTTON_STYLE)
                            ], style={'textAlign': 'center', 'marginBottom': '24px'}),
                            dcc.Graph(id='marketing-demographics-chart', style={'width': '100%', 'height': '600px'}),
                            html.Span(
                                "ⓘ",  # Info icon
                                id="info-icon-marketing-demographics-chart",
                                style={
                                    "fontSize": "20px",
                                    "cursor": "pointer",
                                    "color": "#007BFF",
                                    "position": "relative",  # Relative positioning
                                    "top": "-50px",          # Adjust position slightly
                                    "left": "10px"
                                }
                            ),
                            dbc.Tooltip(
                                [
                                    html.Ul([
                                        html.Li("Users: Marketing, Customer Support Teams"),
                                        html.Li("Purpose: Understand student demographics (gender, age, region) for personalized service and growth."),
                                        html.Li("Chart Details:"),
                                        html.Ul([
                                            html.Li("Pie Chart: Gender distribution (Male, Female)"),
                                            html.Li("Histogram: X = Age groups, Y = Number of students"),
                                            html.Li("Bar Chart: X = Geographic regions, Y = Students per region"),
                                            html.Li("Interactive: Demographic filters with buttons")
                                        ]),
                                        html.Li("Insights:"),
                                        html.Ul([
                                            html.Li("Understand gender and age composition for marketing and course customization."),
                                            html.Li("Identify regions with high/low student participation."),
                                            html.Li("Support regional and demographic-specific outreach.")
                                        ])
                                    ])
                                ],
                                target="info-icon-marketing-demographics-chart",
                                placement="right",
                                style={"fontSize": "14px"}
                            ),
                        ], style=CARD_STYLE)
                    ], id='marketing-content', style={'display': 'none'})
                ]
            )
        ],
        style={
            'backgroundColor': 'transparent',
            'borderBottom': '1px solid #d6d6d6',
            'marginBottom': '24px',
            'padding': '0 24px'
        }
    ),
], style={
    'backgroundColor': COLOR_SCHEME['background'],
    'minHeight': '100vh',
    'padding': '24px',
    'fontFamily': '"Segoe UI", Arial, sans-serif'
})

# Update the tab visibility callback
@app.callback(
    [Output('glimpse-content', 'style'),
     Output('overview-content', 'style'),
     Output('operation-content', 'style'),
     Output('marketing-content', 'style')],
    [Input('tabs', 'value')]
)
def render_content(tab):
    if tab == 'glimpse':
        return {'display': 'block', 'padding': '24px'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}
    elif tab == 'overview':
        return {'display': 'none'}, {'display': 'block'}, {'display': 'none'}, {'display': 'none'}
    elif tab == 'operation':
        return {'display': 'none'}, {'display': 'none'}, {'display': 'block'}, {'display': 'none'}
    elif tab == 'marketing':
        return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'block'}
    return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}


# Add callbacks for the new overview graphs in Glimpse tab
@app.callback(
    Output('overview-revenue-trend', 'figure'),
    [Input('tabs', 'value')]
)
def update_revenue_trend(tab):
    if tab != 'glimpse':
        return {}
    
    monthly_revenue = base_data.groupby(
        base_data['Order_Date'].dt.strftime('%Y-%m')
    )['Amount'].sum().reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly_revenue['Order_Date'],
        y=monthly_revenue['Amount'],
        mode='lines+markers',
        line=dict(color=COLOR_SCHEME['primary'], width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title="Monthly Revenue Trend",
        xaxis_title="Month",
        yaxis_title="Revenue",
        template='plotly_white',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

@app.callback(
    Output('overview-course-dist', 'figure'),
    [Input('tabs', 'value')]
)
def update_course_dist(tab):
    if tab != 'glimpse':
        return {}
    
    course_dist = base_data['Course_Type_Name'].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=course_dist.index,
        values=course_dist.values,
        hole=0.3,
        marker_colors=[COLOR_SCHEME['primary'], COLOR_SCHEME['secondary']]
    )])
    
    fig.update_layout(
        title="Course Type Distribution",
        template='plotly_white',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

@app.callback(
    Output('overview-gender-dist', 'figure'),
    [Input('tabs', 'value')]
)
def update_gender_dist(tab):
    if tab != 'glimpse':
        return {}
    
    gender_dist = base_data['Customer_Gender'].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=gender_dist.index,
        values=gender_dist.values,
        hole=0.3,
        marker_colors=[COLOR_SCHEME['primary'], COLOR_SCHEME['secondary']]
    )])
    
    fig.update_layout(
        title="Gender Distribution",
        template='plotly_white',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

@app.callback(
    Output('overview-age-dist', 'figure'),
    [Input('tabs', 'value')]
)
def update_age_dist(tab):
    if tab != 'glimpse':
        return {}
    
    fig = go.Figure(data=[go.Histogram(
        x=base_data['Customer_Age'],
        nbinsx=20,
        marker_color=COLOR_SCHEME['primary']
    )])
    
    fig.update_layout(
        title="Age Distribution",
        xaxis_title="Age",
        yaxis_title="Count",
        template='plotly_white',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

# Callback for Monthly Revenue Chart
@app.callback(
    Output('monthly-revenue-chart', 'figure'),
    [Input('date-range-combined', 'start_date'),
     Input('date-range-combined', 'end_date'),
     Input('age-range-demo', 'value'),
     Input('course-type-combined', 'value'),
     Input('region-revenue', 'value'),
     Input('gender-dropdown', 'value')],
    prevent_initial_call=False
)
def update_monthly_revenue(start_date, end_date, age_range, course_types, cities, genders):
    filtered_df = base_data.copy()
    
    if start_date and end_date:
        filtered_df = filtered_df[
            (filtered_df['Order_Date'] >= start_date) & 
            (filtered_df['Order_Date'] <= end_date)
        ]
    if age_range:
        filtered_df = filtered_df[(filtered_df['Customer_Age'] >= age_range[0]) & (filtered_df['Customer_Age'] <= age_range[1])]
    if course_types:
        filtered_df = filtered_df[
            filtered_df['Course_Type_Name'].isin(course_types)
        ]
    
    if cities:
        filtered_df = filtered_df[
            filtered_df['City'].isin(cities)
        ]
    if genders:
        filtered_df = filtered_df[filtered_df['Customer_Gender'].isin(genders)]

    # Calculate monthly revenue
    monthly_revenue = filtered_df.groupby(
        filtered_df['Order_Date'].dt.strftime('%Y-%m')
    )['Amount'].sum().reset_index()
    
    # Calculate growth rate
    monthly_revenue['Growth_Rate'] = monthly_revenue['Amount'].pct_change() * 100

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Add revenue bars
    fig.add_trace(
        go.Bar(
            x=monthly_revenue['Order_Date'],
            y=monthly_revenue['Amount'],
            name="Monthly Revenue",
            marker_color=COLOR_SCHEME['secondary']
        ),
        secondary_y=False
    )
    # Add line chart for monthly growth rate
    monthly_revenue['Growth_Rate_Label'] = monthly_revenue['Growth_Rate'].apply(
        lambda x: f"{x:.1f}%"
    )
    # Add growth rate line
    fig.add_trace(
        go.Scatter(
            x=monthly_revenue['Order_Date'],
            y=monthly_revenue['Growth_Rate'],
            name="Growth Rate (%)",
            line=dict(color=COLOR_SCHEME['accent']),
            text=monthly_revenue['Growth_Rate_Label'],
            textposition='top center',  
            textfont=dict(color='#024959'), 
            hovertemplate="Growth Rate: %{text}", 
            mode='lines+markers+text'
        ),
        secondary_y=True
    )

    # Update layout with significantly increased margins and spacing
    fig.update_layout(
        title={
            'text': 'Monthly Revenue Analysis',
            'y': 0.98,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24)
        },
        height=600,  # 增加圖表高度
        margin=dict(
            l=100,   # 增加左邊距
            r=100,   # 增加右邊距
            t=100,   # 顯著增加上邊距
            b=150    # 增加下邊距
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,  # 將圖例往上移更多
            xanchor="center",
            x=0.5,
            font=dict(size=20),
            itemsizing='constant'
        ),
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=18),
            titlefont=dict(size=20),
            title_standoff=30,  # 增加軸標題與圖表的距離
            dtick="M1",  # 設置月份間隔
            tickformat="%b"  # 格式化日期顯示
        ),
        yaxis=dict(
            tickfont=dict(size=18),
            titlefont=dict(size=20),
            title_standoff=30,
            title_text="Revenue",
            rangemode='tozero'
        ),
        yaxis2=dict(
            tickfont=dict(size=18),
            titlefont=dict(size=20),
            title_standoff=30,
            title_text="Growth Rate (%)",
            rangemode='tozero'
        ),
        showlegend=True,
        plot_bgcolor='white',
        bargap=0.2,  # 調整條形圖間距
    )

    # 確保圖表區域有足夠空間
    fig.update_yaxes(
        secondary_y=False,
        automargin=True,  # 自動調整邊距
        ticklabelposition="outside"  # 將刻度標籤放在軸外側
    )
    fig.update_yaxes(
        secondary_y=True,
        automargin=True,
        ticklabelposition="outside"
    )

    return fig

# Callback for Monthly Revenue Chart
@app.callback(
    Output('operation-monthly-revenue-chart', 'figure'),
    [Input('operation-date-range-combined', 'start_date'),
     Input('operation-date-range-combined', 'end_date'),
     Input('operation-age-range-demo', 'value'),
     Input('operation-course-type-combined', 'value'),
     Input('operation-region-revenue', 'value'),
     Input('operation-gender-dropdown', 'value')],
    prevent_initial_call=False
)
def update_monthly_revenue(start_date, end_date, age_range, course_types, cities, genders):
    filtered_df = base_data.copy()
    
    if start_date and end_date:
        filtered_df = filtered_df[
            (filtered_df['Order_Date'] >= start_date) & 
            (filtered_df['Order_Date'] <= end_date)
        ]
    if age_range:
        filtered_df = filtered_df[(filtered_df['Customer_Age'] >= age_range[0]) & (filtered_df['Customer_Age'] <= age_range[1])]
    if course_types:
        filtered_df = filtered_df[
            filtered_df['Course_Type_Name'].isin(course_types)
        ]
    
    if cities:
        filtered_df = filtered_df[
            filtered_df['City'].isin(cities)
        ]
    if genders:
        filtered_df = filtered_df[filtered_df['Customer_Gender'].isin(genders)]

    # Calculate monthly revenue
    monthly_revenue = filtered_df.groupby(
        filtered_df['Order_Date'].dt.strftime('%Y-%m')
    )['Amount'].sum().reset_index()
    
    # Calculate growth rate
    monthly_revenue['Growth_Rate'] = monthly_revenue['Amount'].pct_change() * 100

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Add revenue bars
    fig.add_trace(
        go.Bar(
            x=monthly_revenue['Order_Date'],
            y=monthly_revenue['Amount'],
            name="Monthly Revenue",
            marker_color=COLOR_SCHEME['secondary']
        ),
        secondary_y=False
    )
    # Add line chart for monthly growth rate
    monthly_revenue['Growth_Rate_Label'] = monthly_revenue['Growth_Rate'].apply(
        lambda x: f"{x:.1f}%"
    )
    # Add growth rate line
    fig.add_trace(
        go.Scatter(
            x=monthly_revenue['Order_Date'],
            y=monthly_revenue['Growth_Rate'],
            name="Growth Rate (%)",
            line=dict(color=COLOR_SCHEME['accent']),
            text=monthly_revenue['Growth_Rate_Label'],
            textposition='top center',  
            textfont=dict(color='#024959'), 
            hovertemplate="Growth Rate: %{text}", 
            mode='lines+markers+text'
        ),
        secondary_y=True
    )

    # Update layout with significantly increased margins and spacing
    fig.update_layout(
        title={
            'text': 'Monthly Revenue Analysis',
            'y': 0.98,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24)
        },
        height=600,  # 增加圖表高度
        margin=dict(
            l=100,   # 增加左邊距
            r=100,   # 增加右邊距
            t=100,   # 顯著增加上邊距
            b=150    # 增加下邊距
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,  # 將圖例往上移更多
            xanchor="center",
            x=0.5,
            font=dict(size=20),
            itemsizing='constant'
        ),
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=18),
            titlefont=dict(size=20),
            title_standoff=30,  # 增加軸標題與圖表的距離
            dtick="M1",  # 設置月份間隔
            tickformat="%b"  # 格式化日期顯示
        ),
        yaxis=dict(
            tickfont=dict(size=18),
            titlefont=dict(size=20),
            title_standoff=30,
            title_text="Revenue",
            rangemode='tozero'
        ),
        yaxis2=dict(
            tickfont=dict(size=18),
            titlefont=dict(size=20),
            title_standoff=30,
            title_text="Growth Rate (%)",
            rangemode='tozero'
        ),
        showlegend=True,
        plot_bgcolor='white',
        bargap=0.2,  # 調整條形圖間距
    )

    # 確保圖表區域有足夠空間
    fig.update_yaxes(
        secondary_y=False,
        automargin=True,  # 自動調整邊距
        ticklabelposition="outside"  # 將刻度標籤放在軸外側
    )
    fig.update_yaxes(
        secondary_y=True,
        automargin=True,
        ticklabelposition="outside"
    )

    return fig



# Callback for Booking Heatmap
@app.callback(
    Output('booking-heatmap', 'figure'),
    [Input('date-range-combined', 'start_date'),
     Input('date-range-combined', 'end_date'),
     Input('age-range-demo', 'value'),
     Input('course-type-combined', 'value'),
     Input('region-revenue', 'value'),
     Input('gender-dropdown', 'value')],
    prevent_initial_call=False
)
def update_booking_heatmap(start_date, end_date, age_range, course_types, cities, genders):
    filtered_df = base_data.copy()
    
    # Apply filters
    if start_date and end_date:
        filtered_df = filtered_df[(filtered_df['Order_Date'] >= start_date) & (filtered_df['Order_Date'] <= end_date)]
    if age_range:
        filtered_df = filtered_df[(filtered_df['Customer_Age'] >= age_range[0]) & (filtered_df['Customer_Age'] <= age_range[1])]
    if course_types:
        filtered_df = filtered_df[filtered_df['Course_Type_Name'].isin(course_types)]
    if cities:
        filtered_df = filtered_df[filtered_df['City'].isin(cities)]
    if genders:
        filtered_df = filtered_df[filtered_df['Customer_Gender'].isin(genders)]

    # Add day and month columns
    filtered_df['Day_of_Week'] = filtered_df['Order_Date'].dt.day_name()
    filtered_df['Month'] = filtered_df['Order_Date'].dt.strftime('%Y-%m')

    # Group data for heatmap
    heatmap_data = filtered_df.groupby(['Day_of_Week', 'Month'])['Amount'].sum().reset_index()

    # Define the correct order for days and months
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    #months_order = [
    #    'January', 'February', 'March', 'April', 'May', 'June',
    #    'July', 'August', 'September', 'October', 'November', 'December'
    #]

    # Ensure correct ordering and add missing combinations
    all_combinations = pd.DataFrame(list(itertools.product(days_order)), columns=['Day_of_Week'])
    heatmap_data = all_combinations.merge(heatmap_data, on=['Day_of_Week'], how='left').fillna(0)

    # Pivot the data for the heatmap
    heatmap_pivot = heatmap_data.pivot(index='Day_of_Week', columns='Month', values='Amount').fillna(0)

    # Reindex rows and columns explicitly
    heatmap_pivot = heatmap_pivot.reindex(index=days_order)

    # Create heatmap
    fig = px.imshow(
        heatmap_pivot,
        labels=dict( y="Day of the Week", color="Total Amount"),
        y=days_order,
        color_continuous_scale=[
            [0, "grey"],
            [0.5, "#ffe5bd"],
            [1, "#EDB265"]
        ],
        zmin=0,
        zmax=120000,
        title="Heatmap of Transaction Amount"
    )
    fig.update_layout(
        title={
            'text': 'Student Order Timing Analysis',
            'y': 0.98,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24)
        },
        height=600,  # 增加圖表高度
        margin=dict(
            l=100,   # 增加左邊距
            r=100,   # 增加右邊距
            t=150,   # 顯著增加上邊距
            b=100    # 增加下邊距
        ),
        xaxis=dict(
            title=None,
            tickangle=45,
            tickfont=dict(size=18),
            titlefont=dict(size=20),
            title_standoff=30,  # 增加軸標題與圖表的距離
            dtick="M1",  # 設置月份間隔
            tickformat="%b"  # 格式化日期顯示
        ),
        yaxis=dict(
            tickfont=dict(size=18),
            titlefont=dict(size=20),
            title_standoff=30,
            title_text='Day of Week',
            rangemode='tozero'
        )
    )

    return fig

# Callback for Booking Heatmap
@app.callback(
    Output('marketing-booking-heatmap', 'figure'),
    [Input('marketing-date-range-combined', 'start_date'),
     Input('marketing-date-range-combined', 'end_date'),
     Input('marketing-age-range-demo', 'value'),
     Input('marketing-course-type-combined', 'value'),
     Input('marketing-region-revenue', 'value'),
     Input('marketing-gender-dropdown', 'value')],
    prevent_initial_call=False
)
def update_booking_heatmap(start_date, end_date, age_range, course_types, cities, genders):
    filtered_df = base_data.copy()
    
    # Apply filters
    if start_date and end_date:
        filtered_df = filtered_df[(filtered_df['Order_Date'] >= start_date) & (filtered_df['Order_Date'] <= end_date)]
    if age_range:
        filtered_df = filtered_df[(filtered_df['Customer_Age'] >= age_range[0]) & (filtered_df['Customer_Age'] <= age_range[1])]
    if course_types:
        filtered_df = filtered_df[filtered_df['Course_Type_Name'].isin(course_types)]
    if cities:
        filtered_df = filtered_df[filtered_df['City'].isin(cities)]
    if genders:
        filtered_df = filtered_df[filtered_df['Customer_Gender'].isin(genders)]

    # Add day and month columns
    filtered_df['Day_of_Week'] = filtered_df['Order_Date'].dt.day_name()
    filtered_df['Month'] = filtered_df['Order_Date'].dt.strftime('%Y-%m')

    # Group data for heatmap
    heatmap_data = filtered_df.groupby(['Day_of_Week', 'Month'])['Amount'].sum().reset_index()

    # Define the correct order for days and months
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    #months_order = [
    #    'January', 'February', 'March', 'April', 'May', 'June',
    #    'July', 'August', 'September', 'October', 'November', 'December'
    #]

    # Ensure correct ordering and add missing combinations
    all_combinations = pd.DataFrame(list(itertools.product(days_order)), columns=['Day_of_Week'])
    heatmap_data = all_combinations.merge(heatmap_data, on=['Day_of_Week'], how='left').fillna(0)

    # Pivot the data for the heatmap
    heatmap_pivot = heatmap_data.pivot(index='Day_of_Week', columns='Month', values='Amount').fillna(0)

    # Reindex rows and columns explicitly
    heatmap_pivot = heatmap_pivot.reindex(index=days_order)

    # Create heatmap
    fig = px.imshow(
        heatmap_pivot,
        labels=dict( y="Day of the Week", color="Total Amount"),
        y=days_order,
        color_continuous_scale=[
            [0, "grey"],
            [0.5, "#ffe5bd"],
            [1, "#EDB265"]
        ],
        zmin=0,
        zmax=120000,
        title="Heatmap of Transaction Amount"
    )
    fig.update_layout(
        title={
            'text': 'Student Order Timing Analysis',
            'y': 0.98,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24)
        },
        height=500,  # 增加圖表高度
        margin=dict(
            l=100,   # 增加左邊距
            r=100,   # 增加右邊距
            t=100,   # 顯著增加上邊距
            b=100    # 增加下邊距
        ),
        xaxis=dict(
            title=None,
            tickangle=45,
            tickfont=dict(size=18),
            titlefont=dict(size=20),
            title_standoff=30,  # 增加軸標題與圖表的距離
            dtick="M1",  # 設置月份間隔
            tickformat="%b"  # 格式化日期顯示
        ),
        yaxis=dict(
            tickfont=dict(size=18),
            titlefont=dict(size=20),
            title_standoff=30,
            title_text='Day of Week',
            rangemode='tozero'
        )
    )

    return fig


# Callback for Demographics Chart
@app.callback(
    Output('demographics-chart', 'figure'),
    [Input('date-range-combined', 'start_date'),
     Input('date-range-combined', 'end_date'),
     Input('age-range-demo', 'value'),
     Input('course-type-combined', 'value'),
     Input('region-revenue', 'value'),
     Input('btn-gender', 'n_clicks'),
     Input('btn-age', 'n_clicks'),
     Input('btn-course', 'n_clicks'),
     Input('btn-region', 'n_clicks'),
     Input('btn-age-course', 'n_clicks')],
    prevent_initial_call=False
)
def update_demographics(start_date, end_date, age_range, course_types, cities,
                       n_gender, n_age, n_course, n_region, n_age_course):
    # Initialize empty figure
    fig = go.Figure()

    # Get the button that triggered the callback
    button_id = ctx.triggered_id if ctx.triggered else 'btn-gender'

    # Initial filtering
    filtered_transactions = base_data.copy()
    if start_date and end_date:
        filtered_transactions = filtered_transactions[
            (filtered_transactions['Order_Date'] >= start_date) & 
            (filtered_transactions['Order_Date'] <= end_date)
        ]

    relevant_students = filtered_transactions['Student_id'].unique()
    filtered_df = DA_data[DA_data['StudentID'].isin(relevant_students)].copy()

    if age_range:
        filtered_df = filtered_df[
            (filtered_df['Age'] >= age_range[0]) & 
            (filtered_df['Age'] <= age_range[1])
        ]
    
    if course_types:
        filtered_df = filtered_df[filtered_df['Course_Type_Name'].isin(course_types)]
    
    if cities:
        filtered_df = filtered_df[filtered_df['City'].isin(cities)]

    # Check if filtered data is empty
    if len(filtered_df) == 0:
        fig.add_annotation(
            text="No data available for the selected filters",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=28, color=COLOR_SCHEME['text'])
        )
        return fig

    # Create visualizations based on button clicked
    if button_id == 'btn-gender':
        gender_dist = filtered_df['Gender'].value_counts()
        colors = [COLOR_SCHEME['secondary'], COLOR_SCHEME['accent']]
        fig = go.Figure(data=[go.Pie(
            labels=gender_dist.index,
            values=gender_dist.values,
            hole=0.3,
            textinfo='label+percent',
            textposition='outside',
            marker_colors=colors
        )])
        fig.update_layout(
            title=dict(
                text='Gender Distribution by Selected Region',
                y=0.95,
                x=0.5,
                xanchor='center',
                yanchor='top'
            ),
            title_font_size=24,
            legend=dict(
                font=dict(size=20)
            ),
            uniformtext=dict(
                mode='hide',
                minsize=18
            )
        )

    elif button_id == 'btn-age':
        fig = go.Figure(data=[go.Histogram(
            x=filtered_df['Age'],
            nbinsx=20,
            name='Age Distribution',
            marker_color=COLOR_SCHEME['secondary']
        )])
        fig.update_layout(
            title='Age Distribution by Selected Region',
            xaxis_title='Age',
            yaxis_title='Count'
        )

    elif button_id == 'btn-course':
        course_dist = filtered_df['Course_Type_Name'].value_counts()
        fig = go.Figure(data=[go.Bar(
            x=course_dist.index,
            y=course_dist.values,
            text=course_dist.values,
            textposition='auto',
            marker_color=COLOR_SCHEME['secondary'],
            name='Course Distribution',
            hovertemplate="Course: %{x}<br>Count: %{y}<extra></extra>"
        )])
        fig.update_layout(
            title='Course Type Distribution by Selected Region',
            xaxis_title='Course Type',
            yaxis_title='Count',
            xaxis={'tickangle': 45},
            #showlegend=False
        )

    elif button_id == 'btn-region':
        # Get region distribution for bars
        region_dist = filtered_df['Learning Area'].value_counts().sort_values(ascending=False)
        n_regions = len(region_dist)
        
        # Get unique cities for legend
        cities = filtered_df['City'].unique()
        n_cities = len(cities)
        
        # Generate colors
        colors = px.colors.sequential.Oranges[2:]
        region_colors = colors[:n_regions] if n_regions <= len(colors) else colors * (n_regions // len(colors) + 1)
        
        # Create the bar chart with regions
        fig = go.Figure(data=[go.Bar(
            x=region_dist.index,
            y=region_dist.values,
            text=region_dist.values,
            textposition='auto',
            marker_color=region_colors,
            showlegend=False,  # Hide the region legend
            hovertemplate="Region: %{x}<br>Count: %{y}<extra></extra>"
        )])
        
        # Add invisible scatter traces for city legend
        for idx, city in enumerate(cities):
            fig.add_trace(go.Scatter(
                x=[None],
                y=[None],
                mode='markers',
                marker=dict(color=region_colors[idx]),
                name=city,
                showlegend=True
            ))
        
        fig.update_layout(
            title='Region Distribution (Sorted by Count)',
            xaxis_title='Region',
            yaxis_title='Count',
            xaxis={'tickangle': 45},
            showlegend=True,
            legend=dict(
                font=dict(
                    family='"Segoe UI", Arial, sans-serif',
                    size=28,  # 增加圖例字體大小
                    color=COLOR_SCHEME['text']
                ),
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

    elif button_id == 'btn-age-course':
        # Create age-course distribution
        age_course_dist = filtered_df.groupby(['Age', 'Course_Type_Name']).size().unstack(fill_value=0)
        
        fig = go.Figure()
        colors = px.colors.qualitative.Set3
        
        for idx, course in enumerate(age_course_dist.columns):
            color = colors[idx % len(colors)]
            fig.add_trace(
                go.Scatter(
                    x=age_course_dist.index,
                    y=age_course_dist[course],
                    name=course,
                    mode='lines',
                    stackgroup='one',
                    line=dict(width=0.5),
                    hovertemplate=(
                        "Age: %{x}<br>" +
                        "Count: %{y}<br>" +
                        "<extra></extra>"
                    )
                )
            )
        
        fig.update_layout(
            title='Age Distribution by Course Type in Selected Region',
            xaxis_title='Age',
            yaxis_title='Count',
            hovermode='x unified'
        )

    # Apply common styling
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color=COLOR_SCHEME['text']),
        title_x=0.5,
        title_font=dict(size=24),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig
# Update the chart styling function with larger fonts
def update_chart_layout(fig):
    fig.update_layout(
        template='plotly_white',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={
            'family': '"Segoe UI", Arial, sans-serif',
            'color': COLOR_SCHEME['text'],
            'size': 28
        },
        title_font={
            'family': '"Segoe UI", Arial, sans-serif',
            'color': COLOR_SCHEME['primary'],
            'size': 40
        },
        legend_title_font={
            'family': '"Segoe UI", Arial, sans-serif',
            'color': COLOR_SCHEME['primary']
        },
        hoverlabel={'font': {'size': 28}},
        margin=dict(t=50, l=50, r=50, b=50)
    )
    return fig

# Callback for Demographics Chart
@app.callback(
    Output('marketing-demographics-chart', 'figure'),
    [Input('marketing-date-range-combined', 'start_date'),
     Input('marketing-date-range-combined', 'end_date'),
     Input('marketing-age-range-demo', 'value'),
     Input('marketing-course-type-combined', 'value'),
     Input('marketing-region-revenue', 'value'),
     Input('marketing-btn-gender', 'n_clicks'),
     Input('marketing-btn-age', 'n_clicks'),
     Input('marketing-btn-course', 'n_clicks'),
     Input('marketing-btn-region', 'n_clicks'),
     Input('marketing-btn-age-course', 'n_clicks')],
    prevent_initial_call=False
)
def update_demographics(start_date, end_date, age_range, course_types, cities,
                       n_gender, n_age, n_course, n_region, n_age_course):
    # Initialize empty figure
    fig = go.Figure()

    # Get the button that triggered the callback
    button_id = ctx.triggered_id if ctx.triggered else 'marketing-btn-gender'

    # Initial filtering
    filtered_transactions = base_data.copy()
    if start_date and end_date:
        filtered_transactions = filtered_transactions[
            (filtered_transactions['Order_Date'] >= start_date) & 
            (filtered_transactions['Order_Date'] <= end_date)
        ]

    relevant_students = filtered_transactions['Student_id'].unique()
    filtered_df = DA_data[DA_data['StudentID'].isin(relevant_students)].copy()

    if age_range:
        filtered_df = filtered_df[
            (filtered_df['Age'] >= age_range[0]) & 
            (filtered_df['Age'] <= age_range[1])
        ]
    
    if course_types:
        filtered_df = filtered_df[filtered_df['Course_Type_Name'].isin(course_types)]
    
    if cities:
        filtered_df = filtered_df[filtered_df['City'].isin(cities)]

    # Check if filtered data is empty
    if len(filtered_df) == 0:
        fig.add_annotation(
            text="No data available for the selected filters",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=28, color=COLOR_SCHEME['text'])
        )
        return fig

    # Create visualizations based on button clicked
    if button_id == 'marketing-btn-gender':
        gender_dist = filtered_df['Gender'].value_counts()
        colors = [COLOR_SCHEME['secondary'], COLOR_SCHEME['accent']]
        fig = go.Figure(data=[go.Pie(
            labels=gender_dist.index,
            values=gender_dist.values,
            hole=0.3,
            textinfo='label+percent',
            textposition='outside',
            marker_colors=colors
        )])
        fig.update_layout(
            title=dict(
                text='Gender Distribution by Selected Region',
                y=0.95,
                x=0.5,
                xanchor='center',
                yanchor='top'
            ),
            title_font_size=24,
            legend=dict(
                font=dict(size=20)
            ),
            uniformtext=dict(
                mode='hide',
                minsize=18
            )
        )

    elif button_id == 'marketing-btn-age':
        fig = go.Figure(data=[go.Histogram(
            x=filtered_df['Age'],
            nbinsx=20,
            name='Age Distribution',
            marker_color=COLOR_SCHEME['secondary']
        )])
        fig.update_layout(
            title='Age Distribution by Selected Region',
            xaxis_title='Age',
            yaxis_title='Count'
        )

    elif button_id == 'marketing-btn-course':
        course_dist = filtered_df['Course_Type_Name'].value_counts()
        fig = go.Figure(data=[go.Bar(
            x=course_dist.index,
            y=course_dist.values,
            text=course_dist.values,
            textposition='auto',
            marker_color=COLOR_SCHEME['secondary'],
            name='Course Distribution',
            hovertemplate="Course: %{x}<br>Count: %{y}<extra></extra>"
        )])
        fig.update_layout(
            title='Course Type Distribution by Selected Region',
            xaxis_title='Course Type',
            yaxis_title='Count',
            xaxis={'tickangle': 45},
            #showlegend=False
        )

    elif button_id == 'marketing-btn-region':
        # Get region distribution for bars
        region_dist = filtered_df['Learning Area'].value_counts().sort_values(ascending=False)
        n_regions = len(region_dist)
        
        # Get unique cities for legend
        cities = filtered_df['City'].unique()
        n_cities = len(cities)
        
        # Generate colors
        colors = px.colors.sequential.Oranges[2:]
        region_colors = colors[:n_regions] if n_regions <= len(colors) else colors * (n_regions // len(colors) + 1)
        
        # Create the bar chart with regions
        fig = go.Figure(data=[go.Bar(
            x=region_dist.index,
            y=region_dist.values,
            text=region_dist.values,
            textposition='auto',
            marker_color=region_colors,
            showlegend=False,  # Hide the region legend
            hovertemplate="Region: %{x}<br>Count: %{y}<extra></extra>"
        )])
        
        # Add invisible scatter traces for city legend
        for idx, city in enumerate(cities):
            fig.add_trace(go.Scatter(
                x=[None],
                y=[None],
                mode='markers',
                marker=dict(color=region_colors[idx]),
                name=city,
                showlegend=True
            ))
        
        fig.update_layout(
            title='Region Distribution (Sorted by Count)',
            xaxis_title='Region',
            yaxis_title='Count',
            xaxis={'tickangle': 45},
            showlegend=True,
            legend=dict(
                font=dict(
                    family='"Segoe UI", Arial, sans-serif',
                    size=28,  # 增加圖例字體大小
                    color=COLOR_SCHEME['text']
                ),
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

    elif button_id == 'marketing-btn-age-course':
        # Create age-course distribution
        age_course_dist = filtered_df.groupby(['Age', 'Course_Type_Name']).size().unstack(fill_value=0)
        
        fig = go.Figure()
        colors = px.colors.qualitative.Set3
        
        for idx, course in enumerate(age_course_dist.columns):
            color = colors[idx % len(colors)]
            fig.add_trace(
                go.Scatter(
                    x=age_course_dist.index,
                    y=age_course_dist[course],
                    name=course,
                    mode='lines',
                    stackgroup='one',
                    line=dict(width=0.5),
                    hovertemplate=(
                        "Age: %{x}<br>" +
                        "Count: %{y}<br>" +
                        "<extra></extra>"
                    )
                )
            )
        
        fig.update_layout(
            title='Age Distribution by Course Type in Selected Region',
            xaxis_title='Age',
            yaxis_title='Count',
            hovermode='x unified'
        )

    # Apply common styling
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color=COLOR_SCHEME['text']),
        title_x=0.5,
        title_font=dict(size=24),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig
# Update the chart styling function with larger fonts
def update_chart_layout(fig):
    fig.update_layout(
        template='plotly_white',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={
            'family': '"Segoe UI", Arial, sans-serif',
            'color': COLOR_SCHEME['text'],
            'size': 28
        },
        title_font={
            'family': '"Segoe UI", Arial, sans-serif',
            'color': COLOR_SCHEME['primary'],
            'size': 40
        },
        legend_title_font={
            'family': '"Segoe UI", Arial, sans-serif',
            'color': COLOR_SCHEME['primary']
        },
        hoverlabel={'font': {'size': 28}},
        margin=dict(t=50, l=50, r=50, b=50)
    )
    return fig


# Teacher Class Trend Chart
@app.callback(
    Output('teacher-class-trend', 'figure'),
    [Input('date-range-combined', 'start_date'),
     Input('date-range-combined', 'end_date'),
     Input('age-range-demo', 'value'),
     Input('course-type-combined', 'value'),
     Input('region-revenue', 'value'),
     Input('gender-dropdown', 'value')],
    prevent_initial_call=False
)
def update_teacher_trend(start_date, end_date, age_range, course_types, cities, genders):
    filtered_df = TP_data.copy()
    
    # Remove Unknown data
    filtered_df = filtered_df[
        (filtered_df['Teacher_Name'] != 'Unknown') & 
        (filtered_df['Teacher_Name'].notna())
    ]
    
    # Apply filters
    if start_date and end_date:
        filtered_df = filtered_df[
            (filtered_df['Course_Date'] >= start_date) & 
            (filtered_df['Course_Date'] <= end_date)
        ]
    if age_range:
        filtered_df = filtered_df[
            (filtered_df['Student_Age'] >= age_range[0]) & 
            (filtered_df['Student_Age'] <= age_range[1])
        ]
    if cities:
        filtered_df = filtered_df[filtered_df['Learning_City'].isin(cities)]
    if genders:
        filtered_df = filtered_df[filtered_df['Student_Gender'].isin(genders)]


    # Calculate total classes per teacher
    teacher_totals = filtered_df.groupby('Teacher_Name').size().sort_values(ascending=False)
    
    # Select top 5 and bottom 5 teachers if more than 10 teachers
    if len(teacher_totals) > 10:
        top_teachers = list(teacher_totals.head(5).index)
        #bottom_teachers = list(teacher_totals.tail(5).index)
        #selected_teachers = top_teachers + bottom_teachers
        selected_teachers = top_teachers
        filtered_df = filtered_df[filtered_df['Teacher_Name'].isin(selected_teachers)]

    # Calculate monthly class counts per teacher
    monthly_classes = filtered_df.groupby([
        filtered_df['Course_Date'].dt.strftime('%Y-%m'),
        'Teacher_Name'
    ]).size().reset_index(name='Class_Count')

    # Create figure
    fig = go.Figure()
    # Create data for the bar chart with X-axis as Teacher, Y-axis as Sales, and Color as Month
    teacher_sales_data = monthly_classes.groupby(['Teacher_Name', 'Course_Date'])['Class_Count'].sum().reset_index()
    total_sales_per_teacher = teacher_sales_data.groupby('Teacher_Name')['Class_Count'].sum().sort_values(ascending=False).reset_index()
    total_sales_per_teacher.rename(columns={'Class_Count': 'Total_Sales'}, inplace=True)

    # 定義 selected_teachers 列表，按照 Total_Sales 降序排序
    selected_teachers = total_sales_per_teacher['Teacher_Name'].tolist()

    # 設定 Teacher_Name 的順序，並將數據根據這個順序排序
    teacher_sales_data['Teacher_Name'] = pd.Categorical(
        teacher_sales_data['Teacher_Name'],
        categories=selected_teachers,  # 使用 selected_teachers 列表作為順序
        ordered=True
    )

    # 按照新的 X 軸順序和日期排序
    teacher_sales_data = teacher_sales_data.sort_values(by=['Teacher_Name', 'Course_Date']).reset_index(drop=True)

    teacher_sales_data['Course_Date'] = pd.to_datetime(teacher_sales_data['Course_Date']).dt.strftime('%b')


   # 確保 Course_Date 的排序為正確的月份順序
    teacher_sales_data['Course_Date'] = pd.Categorical(
        teacher_sales_data['Course_Date'],
        categories=[
            'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
        ],
        ordered=True
    )

    # 定義新的顏色映射
    color_mapping = {
        'Jan': "#272727",  # Raisin black
        'Feb': "#9EA7AD",  # Cadet gray
        'Mar': "#E6E6E6",  # Platinum
        'Apr': "#F3CEA3",  # Sunset
        'May': "#FFB65F",  # Earth yellow
        'Jun': "#F89E4A",  # Sandy brown
        'Jul': "#F18635",  # Orange (wheel)
        'Aug': "#CC854E",  # Caramel
        'Sep': "#B6895C",  # New color 1 (焦糖棕調)
        'Oct': "#AA8A6D",  # New color 2 (溫暖米色調)
        'Nov': "#A78466",  # Chamoisee
        'Dec': "#AF8F74",  # Beaver
    }

    # 定義新的顏色映射
    color_mapping = {
        'Jan': "#272727",  # Raisin black
        'Feb': "#63676A",  # Cadet gray
        'Mar': "#9EA7AD",  # Platinum
        'Apr': "#E6E6E6",  # Sunset
        'May': "#F3CEA3",  # Earth yellow
        'Jun': "#F8AE6C",  # Sandy brown
        'Jul': "#FFB65F",  # Orange (wheel)
        'Aug': "#F89E4A",  # Caramel
        'Sep': "#F18635",  # 焦糖棕調
        'Oct': "#CC854E",  # 溫暖米色調
        'Nov': "#AA8A6D",  # Chamoisee
        'Dec': "#A78466"  # 更新顏色 (溫暖棕調)
    }

    # 繪製堆疊條形圖
    fig = go.Figure()

    # 為每個月份添加條形
    for month in teacher_sales_data['Course_Date'].cat.categories:
        month_data = teacher_sales_data[teacher_sales_data['Course_Date'] == month]
        fig.add_trace(go.Bar(
            x=month_data['Teacher_Name'],  # X 軸為教師名稱，順序已按 selected_teachers 排列
            y=month_data['Class_Count'],
            name=month,
            marker_color=color_mapping[month]  # 使用映射的顏色
        ))

    # 更新 layout
    # Sales Volume by Teacher (Sorted by Total Sales)
    fig.update_layout(
        barmode='stack',  # 堆疊模式
        title={
            'text': 'Teacher Performance Analysis',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24)
        },
        xaxis_title="Teacher",
        yaxis_title="Sales Volume",
        height=600,
        margin=dict(l=100, r=100, t=100, b=100),
        legend=dict(
            orientation="v",  # 水平排列
            yanchor="bottom",
            y=0,
            xanchor="center",
            x=9,
            font=dict(size=13),
            title_text="Month"
        ),
        xaxis=dict(
            tickangle=45
        ),
        autosize=True,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    return fig

# Teacher Class Trend Chart
@app.callback(
    Output('operation-teacher-class-trend', 'figure'),
    [Input('operation-date-range-combined', 'start_date'),
     Input('operation-date-range-combined', 'end_date'),
     Input('operation-age-range-demo', 'value'),
     Input('operation-course-type-combined', 'value'),
     Input('operation-region-revenue', 'value'),
     Input('operation-gender-dropdown', 'value')],
    prevent_initial_call=False
)
def update_teacher_trend(start_date, end_date, age_range, course_types, cities, genders):
    filtered_df = TP_data.copy()
    
    # Remove Unknown data
    filtered_df = filtered_df[
        (filtered_df['Teacher_Name'] != 'Unknown') & 
        (filtered_df['Teacher_Name'].notna())
    ]
    
    # Apply filters
    if start_date and end_date:
        filtered_df = filtered_df[
            (filtered_df['Course_Date'] >= start_date) & 
            (filtered_df['Course_Date'] <= end_date)
        ]
    if age_range:
        filtered_df = filtered_df[
            (filtered_df['Student_Age'] >= age_range[0]) & 
            (filtered_df['Student_Age'] <= age_range[1])
        ]
    if cities:
        filtered_df = filtered_df[filtered_df['Learning_City'].isin(cities)]
    if genders:
        filtered_df = filtered_df[filtered_df['Student_Gender'].isin(genders)]


    # Calculate total classes per teacher
    teacher_totals = filtered_df.groupby('Teacher_Name').size().sort_values(ascending=False)
    
    # Select top 5 and bottom 5 teachers if more than 10 teachers
    if len(teacher_totals) > 10:
        top_teachers = list(teacher_totals.head(5).index)
        #bottom_teachers = list(teacher_totals.tail(5).index)
        #selected_teachers = top_teachers + bottom_teachers
        selected_teachers = top_teachers
        filtered_df = filtered_df[filtered_df['Teacher_Name'].isin(selected_teachers)]

    # Calculate monthly class counts per teacher
    monthly_classes = filtered_df.groupby([
        filtered_df['Course_Date'].dt.strftime('%Y-%m'),
        'Teacher_Name'
    ]).size().reset_index(name='Class_Count')

    # Create figure
    fig = go.Figure()
    # Create data for the bar chart with X-axis as Teacher, Y-axis as Sales, and Color as Month
    teacher_sales_data = monthly_classes.groupby(['Teacher_Name', 'Course_Date'])['Class_Count'].sum().reset_index()
    total_sales_per_teacher = teacher_sales_data.groupby('Teacher_Name')['Class_Count'].sum().sort_values(ascending=False).reset_index()
    total_sales_per_teacher.rename(columns={'Class_Count': 'Total_Sales'}, inplace=True)

    # 定義 selected_teachers 列表，按照 Total_Sales 降序排序
    selected_teachers = total_sales_per_teacher['Teacher_Name'].tolist()

    # 設定 Teacher_Name 的順序，並將數據根據這個順序排序
    teacher_sales_data['Teacher_Name'] = pd.Categorical(
        teacher_sales_data['Teacher_Name'],
        categories=selected_teachers,  # 使用 selected_teachers 列表作為順序
        ordered=True
    )

    # 按照新的 X 軸順序和日期排序
    teacher_sales_data = teacher_sales_data.sort_values(by=['Teacher_Name', 'Course_Date']).reset_index(drop=True)

    teacher_sales_data['Course_Date'] = pd.to_datetime(teacher_sales_data['Course_Date']).dt.strftime('%b')


   # 確保 Course_Date 的排序為正確的月份順序
    teacher_sales_data['Course_Date'] = pd.Categorical(
        teacher_sales_data['Course_Date'],
        categories=[
            'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
        ],
        ordered=True
    )

    # 定義新的顏色映射
    color_mapping = {
        'Jan': "#272727",  # Raisin black
        'Feb': "#9EA7AD",  # Cadet gray
        'Mar': "#E6E6E6",  # Platinum
        'Apr': "#F3CEA3",  # Sunset
        'May': "#FFB65F",  # Earth yellow
        'Jun': "#F89E4A",  # Sandy brown
        'Jul': "#F18635",  # Orange (wheel)
        'Aug': "#CC854E",  # Caramel
        'Sep': "#B6895C",  # New color 1 (焦糖棕調)
        'Oct': "#AA8A6D",  # New color 2 (溫暖米色調)
        'Nov': "#A78466",  # Chamoisee
        'Dec': "#AF8F74",  # Beaver
    }

    # 定義新的顏色映射
    color_mapping = {
        'Jan': "#272727",  # Raisin black
        'Feb': "#63676A",  # Cadet gray
        'Mar': "#9EA7AD",  # Platinum
        'Apr': "#E6E6E6",  # Sunset
        'May': "#F3CEA3",  # Earth yellow
        'Jun': "#F8AE6C",  # Sandy brown
        'Jul': "#FFB65F",  # Orange (wheel)
        'Aug': "#F89E4A",  # Caramel
        'Sep': "#F18635",  # 焦糖棕調
        'Oct': "#CC854E",  # 溫暖米色調
        'Nov': "#AA8A6D",  # Chamoisee
        'Dec': "#A78466"  # 更新顏色 (溫暖棕調)
    }

    # 繪製堆疊條形圖
    fig = go.Figure()

    # 為每個月份添加條形
    for month in teacher_sales_data['Course_Date'].cat.categories:
        month_data = teacher_sales_data[teacher_sales_data['Course_Date'] == month]
        fig.add_trace(go.Bar(
            x=month_data['Teacher_Name'],  # X 軸為教師名稱，順序已按 selected_teachers 排列
            y=month_data['Class_Count'],
            name=month,
            marker_color=color_mapping[month]  # 使用映射的顏色
        ))

    # 更新 layout
    fig.update_layout(
        barmode='stack',  # 堆疊模式
        title={
            'text': 'Teacher Performance Analysis',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24)
        },
        xaxis_title="Teacher",
        yaxis_title="Sales Volume",
        height=600,
        margin=dict(l=100, r=100, t=100, b=100),
        legend=dict(
            orientation="v",  # 水平排列
            yanchor="bottom",
            y=0,
            xanchor="center",
            x=9,
            font=dict(size=13),
            title_text="Month"
        ),
        xaxis=dict(
            tickangle=45
        ),
        autosize=True,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    return fig


# Teacher Student Distribution Heatmap
@app.callback(
    Output('teacher-student-heatmap', 'figure'),
    [Input('date-range-combined', 'start_date'),
     Input('date-range-combined', 'end_date'),
     Input('age-range-demo', 'value'),
     Input('course-type-combined', 'value'),
     Input('region-revenue', 'value'),
     Input('gender-dropdown', 'value')],
    prevent_initial_call=False
)
    
def update_teacher_trend(start_date, end_date, age_range, course_types, cities, genders):
    filtered_df = TP_data.copy()
    
    # Remove Unknown data
    filtered_df = filtered_df[
        (filtered_df['Teacher_Name'] != 'Unknown') & 
        (filtered_df['Teacher_Name'].notna())
    ]
    
    # Apply filters
    if start_date and end_date:
        filtered_df = filtered_df[
            (filtered_df['Course_Date'] >= start_date) & 
            (filtered_df['Course_Date'] <= end_date)
        ]
    if age_range:
        filtered_df = filtered_df[
            (filtered_df['Student_Age'] >= age_range[0]) & 
            (filtered_df['Student_Age'] <= age_range[1])
        ]
    if cities:
        filtered_df = filtered_df[filtered_df['Learning_City'].isin(cities)]
    if genders:
        filtered_df = filtered_df[filtered_df['Student_Gender'].isin(genders)]

    # Calculate total classes per teacher
    teacher_totals = filtered_df.groupby('Teacher_Name').size().sort_values(ascending=False)
    
    # Select top 5 and bottom 5 teachers if more than 10 teachers
    if len(teacher_totals) > 10:
        top_teachers = list(teacher_totals.head(5).index)
        #bottom_teachers = list(teacher_totals.tail(5).index)
        #selected_teachers = top_teachers + bottom_teachers
        selected_teachers = top_teachers
        filtered_df = filtered_df[filtered_df['Teacher_Name'].isin(selected_teachers)]

    #filtered_df = TP_data.copy()
    
    # 打印列名以檢查
    print("Available columns:", filtered_df.columns.tolist())
    
    # Remove Unknown data
    filtered_df = filtered_df[
        (filtered_df['Teacher_Name'].notna()) & 
        (filtered_df['Teacher_Name'] != 'Unknown')
    ]
    
    # Apply filters
    if start_date and end_date:
        filtered_df = filtered_df[
            (filtered_df['Course_Date'] >= start_date) & 
            (filtered_df['Course_Date'] <= end_date)
        ]
    if age_range:
        filtered_df = filtered_df[
            (filtered_df['Student_Age'] >= age_range[0]) & 
            (filtered_df['Student_Age'] <= age_range[1])
        ]
    if cities:
        filtered_df = filtered_df[filtered_df['Learning_City'].isin(cities)]
    if genders:
        filtered_df = filtered_df[filtered_df['Student_Gender'].isin(genders)]

    # Create student age groups
    filtered_df['Age_Group'] = pd.cut(
        filtered_df['Student_Age'],
        bins=[0, 20, 30, 40, 50, 100],
        labels=['0-20', '21-30', '31-40', '41-50', '50+']
    )

    # 確認 Student_ID 列名
    student_id_column = 'Student_ID'  # 確保這是正確的列名
    if student_id_column not in filtered_df.columns:
        raise KeyError(f"Column '{student_id_column}' not found in DataFrame")

    # Count unique students per teacher and age group
    unique_students = filtered_df.groupby(['Teacher_Name', 'Age_Group'])[student_id_column].nunique().reset_index()

    # Pivot the data
    heatmap_data = unique_students.pivot(
        index='Teacher_Name', 
        columns='Age_Group', 
        values=student_id_column
    ).fillna(0)

    # Calculate total unique students per teacher for sorting
    teacher_totals = filtered_df.groupby('Teacher_Name')[student_id_column].nunique().sort_values(ascending=False)
    
    # Select top 10 teachers if more than 10 teachers
    if len(teacher_totals) > 5:
        selected_teachers = list(teacher_totals.head(5).index)
        heatmap_data = heatmap_data.loc[selected_teachers]
        teacher_totals = teacher_totals[selected_teachers]

    # Sort heatmap data by total students
    heatmap_data = heatmap_data.loc[teacher_totals.index]

    # Create heatmap
    fig = px.imshow(
        heatmap_data,
        labels=dict(x="Age Group", y="Teacher", color="Number of Unique Students"),
        color_continuous_scale=[
            [0, "grey"],
            [0.5, "#ffe5bd"],
            [1, "#EDB265"]
        ],
        aspect="auto"
    )

    # Update layout
    # Teacher-Student Age Distribution (Unique Students)
    title_text = 'Teacher Audience Analysis'
    if len(teacher_totals) > 5:
        title_text += ' (Top 5 Teachers)'
        
    fig.update_layout(
        title={
            'text': title_text,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24)
        },
        height=500,
        margin=dict(l=100, r=100, t=100, b=100),
        xaxis=dict(
            tickangle=0,
            tickfont=dict(size=18),
            titlefont=dict(size=20)
        ),
        yaxis=dict(
            tickfont=dict(size=18),
            titlefont=dict(size=20),
            title="Teacher (Unique Students)"
        )
    )

    # Add total unique students to y-axis labels
    #fig.update_yaxes(
    #    ticktext=[f"{teacher} ({int(teacher_totals[teacher])} students)" 
    #             for teacher in heatmap_data.index],
    #    tickvals=list(range(len(heatmap_data.index)))
    #)

    return fig

@app.callback(
    Output('marketing-teacher-student-heatmap', 'figure'),
    [Input('marketing-date-range-combined', 'start_date'),
     Input('marketing-date-range-combined', 'end_date'),
     Input('marketing-age-range-demo', 'value'),
     Input('marketing-course-type-combined', 'value'),
     Input('marketing-region-revenue', 'value'),
     Input('marketing-gender-dropdown', 'value')],
    prevent_initial_call=False
)
    
def update_teacher_trend(start_date, end_date, age_range, course_types, cities, genders):
    filtered_df = TP_data.copy()
    
    # Remove Unknown data
    filtered_df = filtered_df[
        (filtered_df['Teacher_Name'] != 'Unknown') & 
        (filtered_df['Teacher_Name'].notna())
    ]
    
    # Apply filters
    if start_date and end_date:
        filtered_df = filtered_df[
            (filtered_df['Course_Date'] >= start_date) & 
            (filtered_df['Course_Date'] <= end_date)
        ]
    if age_range:
        filtered_df = filtered_df[
            (filtered_df['Student_Age'] >= age_range[0]) & 
            (filtered_df['Student_Age'] <= age_range[1])
        ]
    if cities:
        filtered_df = filtered_df[filtered_df['Learning_City'].isin(cities)]
    if genders:
        filtered_df = filtered_df[filtered_df['Student_Gender'].isin(genders)]

    # Calculate total classes per teacher
    teacher_totals = filtered_df.groupby('Teacher_Name').size().sort_values(ascending=False)
    
    # Select top 5 and bottom 5 teachers if more than 10 teachers
    if len(teacher_totals) > 10:
        top_teachers = list(teacher_totals.head(5).index)
        #bottom_teachers = list(teacher_totals.tail(5).index)
        #selected_teachers = top_teachers + bottom_teachers
        selected_teachers = top_teachers
        filtered_df = filtered_df[filtered_df['Teacher_Name'].isin(selected_teachers)]

    #filtered_df = TP_data.copy()
    
    # 打印列名以檢查
    print("Available columns:", filtered_df.columns.tolist())
    
    # Remove Unknown data
    filtered_df = filtered_df[
        (filtered_df['Teacher_Name'].notna()) & 
        (filtered_df['Teacher_Name'] != 'Unknown')
    ]
    
    # Apply filters
    if start_date and end_date:
        filtered_df = filtered_df[
            (filtered_df['Course_Date'] >= start_date) & 
            (filtered_df['Course_Date'] <= end_date)
        ]
    if age_range:
        filtered_df = filtered_df[
            (filtered_df['Student_Age'] >= age_range[0]) & 
            (filtered_df['Student_Age'] <= age_range[1])
        ]
    if cities:
        filtered_df = filtered_df[filtered_df['Learning_City'].isin(cities)]
    if genders:
        filtered_df = filtered_df[filtered_df['Student_Gender'].isin(genders)]

    # Create student age groups
    filtered_df['Age_Group'] = pd.cut(
        filtered_df['Student_Age'],
        bins=[0, 20, 30, 40, 50, 100],
        labels=['0-20', '21-30', '31-40', '41-50', '50+']
    )

    # 確認 Student_ID 列名
    student_id_column = 'Student_ID'  # 確保這是正確的列名
    if student_id_column not in filtered_df.columns:
        raise KeyError(f"Column '{student_id_column}' not found in DataFrame")

    # Count unique students per teacher and age group
    unique_students = filtered_df.groupby(['Teacher_Name', 'Age_Group'])[student_id_column].nunique().reset_index()

    # Pivot the data
    heatmap_data = unique_students.pivot(
        index='Teacher_Name', 
        columns='Age_Group', 
        values=student_id_column
    ).fillna(0)

    # Calculate total unique students per teacher for sorting
    teacher_totals = filtered_df.groupby('Teacher_Name')[student_id_column].nunique().sort_values(ascending=False)
    
    # Select top 10 teachers if more than 10 teachers
    if len(teacher_totals) > 5:
        selected_teachers = list(teacher_totals.head(5).index)
        heatmap_data = heatmap_data.loc[selected_teachers]
        teacher_totals = teacher_totals[selected_teachers]

    # Sort heatmap data by total students
    heatmap_data = heatmap_data.loc[teacher_totals.index]

    # Create heatmap
    fig = px.imshow(
        heatmap_data,
        labels=dict(x="Age Group", y="Teacher", color="Number of Unique Students"),
        color_continuous_scale=[
            [0, "grey"],
            [0.5, "#ffe5bd"],
            [1, "#EDB265"]
        ],
        aspect="auto"
    )

    # Update layout
    title_text = 'Teacher Audience Analysis'
    if len(teacher_totals) > 5:
        title_text += ' (Top 5 Teachers)'
        
    fig.update_layout(
        title={
            'text': title_text,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24)
        },
        height=500,
        margin=dict(l=100, r=100, t=100, b=100),
        xaxis=dict(
            tickangle=0,
            tickfont=dict(size=18),
            titlefont=dict(size=20)
        ),
        yaxis=dict(
            tickfont=dict(size=18),
            titlefont=dict(size=20),
            title="Teacher (Unique Students)"
        )
    )

    # Add total unique students to y-axis labels
    #fig.update_yaxes(
    #    ticktext=[f"{teacher} ({int(teacher_totals[teacher])} students)" 
    #             for teacher in heatmap_data.index],
    #    tickvals=list(range(len(heatmap_data.index)))
    #)

    return fig


if __name__ == '__main__':
    app.run(debug=True)
