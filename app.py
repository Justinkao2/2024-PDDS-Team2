import sqlite3
import pandas as pd
from dash import Dash, html, dcc, Input, Output, ctx
import plotly.graph_objects as go
import plotly.express as px
import plotly.colors as pc
from plotly.subplots import make_subplots 
import itertools

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
    # Header with gradient
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
        'background': '#ffffff',  # White background
        'marginBottom': '32px',
        'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
        'padding': '24px',
        'border': f'1px solid {COLOR_SCHEME["secondary"]}'  # Added subtle border
    }),
    
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
                options=[{'label': gender, 'value': gender} for gender in base_data['Customer_Gender'].unique()],
                multi=True,
                style={'borderRadius': '8px', 'fontSize': '28px'}
            ),
        ], style={'flex': '1'})
    ], style={**CARD_STYLE, 'display': 'flex', 'alignItems': 'flex-end', 'gap': '24px'}),
    
    # Revenue Analysis Section
    html.Div([
        html.H2("Revenue & Booking Analysis", 
                style=TEXT_STYLES['section_header']),
        html.Div([
            # Add specific widths and adjust margins for both graphs
            dcc.Graph(
                id='monthly-revenue-chart', 
                style={
                    'width': '48%',  # Adjust width to leave proper spacing
                    'display': 'inline-block',
                    'marginRight': '2%'
                }
            ),
            dcc.Graph(
                id='booking-heatmap', 
                style={
                    'width': '48%',  # Adjust width to leave proper spacing
                    'display': 'inline-block',
                    'marginLeft': '2%'
                }
            )
        ], style={
            'display': 'flex',
            'justifyContent': 'center',  # Center the graphs horizontally
            'alignItems': 'center',      # Center the graphs vertically
            'width': '100%'              # Ensure full width usage
        })
    ], style=CARD_STYLE),
    
    # Teacher Performance Analysis Section
    html.Div([
        html.H2("Teacher Performance Analysis", 
                style=TEXT_STYLES['section_header']),
        html.Div([
            dcc.Graph(
                id='teacher-class-trend', 
                style={
                    'width': '48%',
                    'display': 'inline-block',
                    'marginRight': '2%',
                    'height': '500px'
                }
            ),
            dcc.Graph(
                id='teacher-student-heatmap', 
                style={
                    'width': '48%',
                    'display': 'inline-block',
                    'marginLeft': '2%'
                }
            )
        ], style={
            'display': 'flex',
            'justifyContent': 'center',
            'alignItems': 'center',
            'width': '100%'
        })
    ], style=CARD_STYLE),
    
    # Demographics Section
    html.Div([
        html.H2("Demographics Analysis", 
                style=TEXT_STYLES['section_header']),
        html.Div([
            html.Button('Gender Distribution', id='btn-gender', n_clicks=0, style=BUTTON_STYLE),
            html.Button('Age Distribution', id='btn-age', n_clicks=0, style=BUTTON_STYLE),
            html.Button('Course Distribution', id='btn-course', n_clicks=0, style=BUTTON_STYLE),
            html.Button('Region Distribution', id='btn-region', n_clicks=0, style=BUTTON_STYLE),
            html.Button('Age by Course Type', id='btn-age-course', n_clicks=0, style=BUTTON_STYLE)
        ], style={'textAlign': 'center', 'marginBottom': '24px'}),
        dcc.Graph(id='demographics-chart')
    ], style=CARD_STYLE)
], style={
    'backgroundColor': COLOR_SCHEME['background'],
    'minHeight': '100vh',
    'padding': '24px',
    'fontFamily': '"Segoe UI", Arial, sans-serif'
})

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
            tickformat="%b %Y"  # 格式化日期顯示
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
            tickangle=45,
            tickfont=dict(size=18),
            titlefont=dict(size=20),
            title_standoff=30,  # 增加軸標題與圖表的距離
            dtick="M1",  # 設置月份間隔
            tickformat="%b %Y"  # 格式化日期顯示
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
        colors = px.colors.sequential.Blues[2:]
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

    # 確保 Course_Date 的排序為正確的月份順序
    teacher_sales_data['Course_Date'] = pd.Categorical(
        teacher_sales_data['Course_Date'],
        categories=[
            '2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06',
            '2024-07', '2024-08', '2024-09', '2024-10', '2024-11', '2024-12'
        ],
        ordered=True
    )

    # 定義顏色映射
    color_mapping = {
        '2024-01': "#FFF4CC",
        '2024-02': "#FFE066",
        '2024-03': "#FFC107",
        '2024-04': "#FFCDD2",
        '2024-05': "#F44336",
        '2024-06': "#B71C1C",
        '2024-07': "#AED581",
        '2024-08': "#81C784",
        '2024-09': "#388E3C",
        '2024-10': "#90CAF9",
        '2024-11': "#2196F3",
        '2024-12': "#0D47A1",
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
            'text': 'Sales Volume by Teacher (Sorted by Total Sales)',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=24)
        },
        xaxis_title="Teacher",
        yaxis_title="Sales Volume",
        height=800,
        margin=dict(l=100, r=100, t=150, b=100),
        legend=dict(
            orientation="v",  # 水平排列
            yanchor="bottom",
            y=-0.2,
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
    title_text = 'Teacher-Student Age Distribution (Unique Students)'
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
        height=600,
        margin=dict(l=100, r=100, t=150, b=100),
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
