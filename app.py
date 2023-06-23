from flask import Flask,redirect,url_for,render_template,request,flash,abort,session,send_file
from flask_session import Session
from key import secret_key,salt1,salt2
from stoken import token
from cmail import sendmail
from itsdangerous import URLSafeTimedSerializer
import mysql.connector
from io import BytesIO
app=Flask(__name__)
app.secret_key=secret_key
app.config['SESSION_TYPE']='filesystem'
Session(app)
mydb=mysql.connector.connect(host='localhost',user='root',password='admin',db='students')
@app.route('/')
def index():
    return render_template('title.html')
@app.route('/admin')
def admin():
    return render_template('admin.html')
@app.route('/adminlogin',methods=['GET','POST'])
def adlogin():
    if session.get('user'):
        return redirect(url_for('adhome'))
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from admin where username=%s',[username])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.execute('select count(*) from admin where username=%s and password=%s',[username,password])
            p_count=cursor.fetchone()[0]
            if p_count==1:
                session['user']=username
                cursor.execute('select email_status from admin where username=%s',[username])
                status=cursor.fetchone()[0]
                cursor.close()
                if status!='confirmed':
                    return redirect(url_for('adinactive'))
                else:
                    return redirect(url_for('adhome'))
            else:
                cursor.close()
                flash('invalid password')
                return render_template('adminlogin.html')
        else:
            cursor.close()
            flash('invalid username')
            return render_template('adminlogin.html')
    return render_template('adminlogin.html')
@app.route('/admininactive')
def adinactive():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from admin where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            return redirect(url_for('adhome'))
        else:
            return render_template('admininactive.html')
    else:
        return redirect(url_for('adlogin'))
@app.route('/adminhomepage',methods=['GET','POST'])
def adhome():
    return render_template('adminhomepage.html')
@app.route('/adhome')
def adminhome():
    return render_template('home.html')
@app.route('/adminresendconfirmation')
def adresend():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from admin where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.execute('select email from admin where username=%s',[username])
        email=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('adhome'))
        else:
            subject='Email Confirmation'
            confirm_link=url_for('adconfirm',token=token(email,salt1),_external=True)
            body=f"Please confirm your mail-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return redirect(url_for('adinactive'))
    else:
        return redirect(url_for('adlogin'))
@app.route('/adminregistration',methods=['GET','POST'])
def adregistration():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        try:
            cursor.execute('insert into admin (username,password,email) values(%s,%s,%s)',(username,password,email))
        except mysql.connector.IntegrityError:
            flash('Username or email is already in use')
            return render_template('adminregistration.html')
        else:
            mydb.commit()
            cursor.close()
            subject='Email Confirmation'
            confirm_link=url_for('adconfirm',token=token(email,salt1),_external=True)
            body=f"Thanks for signing up.Follow this link-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return render_template('adminregistration.html')
    return render_template('adminregistration.html')
    
@app.route('/adminconfirm/<token>')
def adconfirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt1,max_age=120)
    except Exception as e:
        #print(e)
        abort(404,'Link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from admin where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('adlogin'))
        else:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("update admin set email_status='confirmed' where email=%s",[email])
            mydb.commit()
            flash('Email confirmation success')
            return redirect(url_for('adlogin'))
@app.route('/adminforget',methods=['GET','POST'])
def adforgot():
    if request.method=='POST':
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from admin where email=%s',[email])
        count=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('SELECT email_status from admin where email=%s',[email])
            status=cursor.fetchone()[0]
            cursor.close()
            if status!='confirmed':
                flash('Please Confirm your email first')
                return render_template('adminforgot.html')
            else:
                subject='Forget Password'
                confirm_link=url_for('adreset',token=token(email,salt=salt2),_external=True)
                body=f"Use this link to reset your password-\n\n{confirm_link}"
                sendmail(to=email,body=body,subject=subject)
                flash('Reset link sent check your email')
                return redirect(url_for('adlogin'))
        else:
            flash('Invalid email id')
            return render_template('adminforgot.html')
    return render_template('adminforgot.html')
@app.route('/adminreset/<token>',methods=['GET','POST'])
def adreset(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt2,max_age=180)
    except:
        abort(404,'Link Expired')
    else:
        if request.method=='POST':
            newpassword=request.form['npassword']
            confirmpassword=request.form['cpassword']
            if newpassword==confirmpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update admin set password=%s where email=%s',[newpassword,email])
                mydb.commit()
                flash('Reset Successful')
                return redirect(url_for('adlogin'))
            else:
                flash('Passwords mismatched')
                return render_template('adminnewpassword.html')
        return render_template('adminnewpassword.html')

@app.route('/adminlogout')
def adlogout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('adlogin'))
    else:
        return redirect(url_for('adlogin'))
@app.route('/viewgrievence')
def viewgrievence():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(cid) as uid,problemtitle,date from complaint')
        data=cursor.fetchall()
        cursor.close()
        return render_template('gtable.html',data=data)
    else:
        return redirect(url_for('adlogin'))
@app.route('/gcid/<uid>')
def gcid(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(cid),studentname,studentrollno,branch,year,email,problemtitle,problemcontent,date from complaint where bin_to_uuid(cid)=%s',[uid])
        cursor.close()
        uid,name,rollno,branch,year,email,title,content,date=cursor.fetchone()
        return render_template('viewgrievence.html',name=name,rollno=rollno,branch=branch,year=year,email=email,title=title,content=content,date=date)
    else:
        return redirect(url_for('adlogin'))
@app.route('/gcfid/<uid>')
def gcfid(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select extension,filedata from complaint where bin_to_uuid(cid)=%s',[uid])
        ext,bin_data=cursor.fetchone()
        bytes_data=BytesIO(bin_data)
        filename=f'attachement.{ext}'
        return send_file(bytes_data,download_name=filename,as_attachment=False)
    else:   
        return redirect(url_for('adlogin'))
@app.route('/grievenceupadate/<uid>',methods=['GET','POST'])
def statusupdate(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(cid),studentname,studentrollno,branch,year,email,problemtitle,problemcontent,status from complaint where bin_to_uuid(cid)=%s',[uid])
        uid,name,rollno,branch,year,email,title,content,status=cursor.fetchone()
        cursor.close()
        if request.method=='POST':
            status=request.form['status']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('update complaint set status=%s where bin_to_uuid(cid)=%s',[status,uid])
            mydb.commit()
            cursor.close()
            flash('Complaint Status upated successfully')
            return redirect(url_for('viewgrievence'))
        return render_template('grievenceupdate.html',status=status)
    else:
        return redirect(url_for('adlogin'))
@app.route('/statusmail/<uid>')
def statusmail(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select status from complaint where bin_to_uuid(cid)=%s',[uid])
        status=cursor.fetchone()[0]
        cursor.execute('select email from complaint where bin_to_uuid(cid)=%s',[uid])
        email=cursor.fetchone()[0]
        cursor.close()
        if status=='Resolved':
            subject='Complaint Status'
            body=f"complaint status Resolved"
            sendmail(to=email,body=body,subject=subject)
            return redirect(url_for('viewgrievence'))
        else:
            subject='Complaint Status'
            body=f"complaint status In Progress"
            sendmail(to=email,body=body,subject=subject)
            return redirect(url_for('viewgrievence'))
    else:
        return redirect(url_for('adlogin'))
@app.route('/adviewapplication')
def adviewapplication():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(aid) as uid,date,name from apply')
        data=cursor.fetchall()
        cursor.close()
        return render_template('aptable.html',data=data)
    else:
        return redirect(url_for('adlogin'))
@app.route('/daid/<uid>')
def daid(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(aid),name,fname,religion,nationality,caste,handicaped,address,email,tmarks,imarks,status,date from apply where bin_to_uuid(aid)=%s',[uid])
        cursor.close()
        uid,name,fname,religion,nationality,caste,handicaped,address,email,tmarks,imarks,status,date=cursor.fetchone()
        return render_template('adviewapplication.html',name=name,fname=fname,religion=religion,nationality=nationality,caste=caste,handicaped=handicaped,address=address,email=email,tmarks=tmarks,imarks=imarks,status=status,date=date)
    else:
        return redirect(url_for('adlogin'))
@app.route('/dafid/<uid>')
def dafid(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select extension,filedata from apply where bin_to_uuid(aid)=%s',[uid])
        ext,bin_data=cursor.fetchone()
        bytes_data=BytesIO(bin_data)
        filename=f'attachement.{ext}'
        return send_file(bytes_data,download_name=filename,as_attachment=False)
    else:   
        return redirect(url_for('adlogin'))
@app.route('/applicationupdate/<uid>',methods=['GET','POST'])
def applicationupdate(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(aid),name,fname,religion,nationality,caste,handicaped,address,email,tmarks,imarks,status from apply where bin_to_uuid(aid)=%s',[uid])
        uid,name,fname,religion,nationality,caste,handicaped,address,email,tmarks,imarks,status=cursor.fetchone()
        cursor.close()
        if request.method=='POST':
            status=request.form['status']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('update apply set status=%s where bin_to_uuid(aid)=%s',[status,uid])
            mydb.commit()
            cursor.close()
            flash('Application Status upated successfully')
            return redirect(url_for('adviewapplication'))
        return render_template('applicationstatus.html',status=status)
    else:
        return redirect(url_for('adlogin'))
@app.route('/astatusmail/<uid>')
def astatusmail(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select status from apply where bin_to_uuid(aid)=%s',[uid])
        status=cursor.fetchone()[0]
        cursor.execute('select email from apply where bin_to_uuid(aid)=%s',[uid])
        email=cursor.fetchone()[0]
        cursor.close()
        if status=='Accepted':
            subject='Application Status'
            body=f"complaint status Accepted"
            sendmail(to=email,body=body,subject=subject)
            return redirect(url_for('adviewapplication'))
        elif status=='Rejected':
            subject='Application Status'
            body=f"complaint status Rejected"
            sendmail(to=email,body=body,subject=subject)
            return redirect(url_for('adviewapplication'))
        else:
            subject='Application Status'
            body=f"complaint status Waiting"
            sendmail(to=email,body=body,subject=subject)
            return redirect(url_for('adviewapplication'))
    else:
        return redirect(url_for('adlogin'))
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where username=%s',[username])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.execute('select count(*) from users where username=%s and password=%s',[username,password])
            p_count=cursor.fetchone()[0]
            if p_count==1:
                session['user']=username
                cursor.execute('select email_status from users where username=%s',[username])
                status=cursor.fetchone()[0]
                cursor.close()
                if status!='confirmed':
                    return redirect(url_for('adinactive'))
                else:
                    return redirect(url_for('home'))
            else:
                cursor.close()
                flash('invalid password')
                return render_template('login.html')
        else:
            cursor.close()
            flash('invalid username')
            return render_template('login.html')
    return render_template('login.html')
@app.route('/inactive')
def inactive():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            return redirect(url_for('home'))
        else:
            return render_template('inactive.html')
    else:
        return redirect(url_for('login'))
@app.route('/homepage',methods=['GET','POST'])
def home():
    return render_template('homepage.html')
@app.route('/shome')
def shome():
    return render_template('shome.html')
@app.route('/resendconfirmation')
def resend():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.execute('select email from users where username=%s',[username])
        email=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('home'))
        else:
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Please confirm your mail-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('login'))
@app.route('/registration',methods=['GET','POST'])
def registration():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        try:
            cursor.execute('insert into users (username,password,email) values(%s,%s,%s)',(username,password,email))
        except mysql.connector.IntegrityError:
            flash('Username or email is already in use')
            return render_template('registration.html')
        else:
            mydb.commit()
            cursor.close()
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Thanks for signing up.Follow this link-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return render_template('registration.html')
    return render_template('registration.html')
    
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt1,max_age=120)
    except Exception as e:
        #print(e)
        abort(404,'Link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('login'))
        else:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("update users set email_status='confirmed' where email=%s",[email])
            mydb.commit()
            flash('Email confirmation success')
            return redirect(url_for('login'))
@app.route('/forget',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where email=%s',[email])
        count=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('SELECT email_status from users where email=%s',[email])
            status=cursor.fetchone()[0]
            cursor.close()
            if status!='confirmed':
                flash('Please Confirm your email first')
                return render_template('forgot.html')
            else:
                subject='Forget Password'
                confirm_link=url_for('reset',token=token(email,salt=salt2),_external=True)
                body=f"Use this link to reset your password-\n\n{confirm_link}"
                sendmail(to=email,body=body,subject=subject)
                flash('Reset link sent check your email')
                return redirect(url_for('login'))
        else:
            flash('Invalid email id')
            return render_template('forgot.html')
    return render_template('forgot.html')
@app.route('/reset/<token>',methods=['GET','POST'])
def reset(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt2,max_age=180)
    except:
        abort(404,'Link Expired')
    else:
        if request.method=='POST':
            newpassword=request.form['npassword']
            confirmpassword=request.form['cpassword']
            if newpassword==confirmpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update users set password=%s where email=%s',[newpassword,email])
                mydb.commit()
                flash('Reset Successful')
                return redirect(url_for('login'))
            else:
                flash('Passwords mismatched')
                return render_template('newpassword.html')
        return render_template('newpassword.html')

@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))
@app.route('/raisecomplaint',methods=['GET','POST'])
def complaint():
    if session.get('user'):
        if request.method=='POST':
            name=request.form['name']
            rollno=request.form['rollno']
            branch=request.form['branch']
            year=request.form['year']
            email=request.form['email']
            title=request.form['title']
            content=request.form['content']
            files=request.files.getlist('file')
            username=session.get('user')
            cursor=mydb.cursor(buffered=True)
            for file in files:
                file_ext=file.filename.split('.')[-1]
                file_data=file.read()#reads binary data from file
                cursor.execute('insert into complaint (cid,studentname,studentrollno,branch,year,email,problemtitle,problemcontent,extension,filedata,added_by) values(UUID_TO_BIN(UUID()),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',[name,rollno,branch,year,email,title,content,file_ext,file_data,username,])
                mydb.commit()
            cursor.close()
            flash('complaint added successfully')
            return redirect(url_for('viewcomplaint'))
        return render_template('complaint.html')
    else:
        return redirect(url_for('login'))
    return render_template('complaint.html')
@app.route('/viewcomplaint')
def viewcomplaint():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(cid) as uid,problemtitle,date  from complaint where added_by=%s order by date desc',[username])
        data=cursor.fetchall()
        cursor.close()
        return render_template('table.html',data=data)
    else:
        return redirect(url_for('login'))
@app.route('/cid/<uid>')
def vcid(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(cid),studentname,studentrollno,branch,year,email,problemtitle,problemcontent,date from complaint where bin_to_uuid(cid)=%s',[uid])
        cursor.close()
        uid,name,rollno,branch,year,email,title,content,date=cursor.fetchone()
        return render_template('viewcomplaint.html',name=name,rollno=rollno,branch=branch,year=year,email=email,title=title,content=content,date=date)
    else:
        return redirect(url_for('login'))
@app.route('/cfid/<uid>')
def cfid(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select extension,filedata from complaint where bin_to_uuid(cid)=%s',[uid])
        ext,bin_data=cursor.fetchone()
        bytes_data=BytesIO(bin_data)
        filename=f'attachement.{ext}'
        return send_file(bytes_data,download_name=filename,as_attachment=False)
    else:   
        return redirect(url_for('login'))
@app.route('/cstatus/<uid>')
def cstatus(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select status from complaint where bin_to_uuid(cid)=%s',[uid])
        status=cursor.fetchone()[0]
        cursor.close()
        return render_template('cstatus.html',status=status)
    else:
        return redirect(url_for('login'))
@app.route('/delete/<uid>')
def delete(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('delete from complaint where bin_to_uuid(cid)=%s',[uid])
        mydb.commit()
        cursor.close()
        flash('complaint deleted successfully')
        return redirect(url_for('viewcomplaint'))
    else:
        return redirect(url_for('login'))
@app.route('/application',methods=['GET','POST'])
def application():
    if session.get('user'):
        if request.method=='POST':
            name=request.form['name']
            fname=request.form['fname']
            religion=request.form['religion']
            nationality=request.form['nationality']
            caste=request.form['caste']
            handicaped=request.form['handicaped']
            address=request.form['address']
            email=request.form['email']
            tmarks=request.form['tmarks']
            imarks=request.form['imarks']
            files=request.files.getlist('file')
            username=session.get('user')
            cursor=mydb.cursor(buffered=True)
            try:
                for file in files:
                    file_ext=file.filename.split('.')[-1]
                    file_data=file.read()#reads binary data from file
                    cursor.execute('insert into apply (aid,name,fname,religion,nationality,caste,handicaped,address,email,tmarks,imarks,extension,filedata,added_by) values(UUID_TO_BIN(UUID()),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',[name,fname,religion,nationality,caste,handicaped,address,email,tmarks,imarks,file_ext,file_data,username])
            except mysql.connector.IntegrityError:
                flash('Address is already used')
                return render_template('application.html')
            else:
                mydb.commit()
                cursor.close()
                flash('Application successful')
                return redirect(url_for('viewapplication'))
        return render_template('application.html')
    else:
        return redirect(url_for('login'))
    return render_template('application.html')
@app.route('/viewapplication')
def viewapplication():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(aid) as uid,date,name from apply where added_by=%s order by date desc',[username])
        data=cursor.fetchall()
        cursor.close()
        return render_template('atable.html',data=data)
    else:
        return redirect(url_for('login'))
@app.route('/aid/<uid>')
def vaid(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(aid),name,fname,religion,nationality,caste,handicaped,address,email,tmarks,imarks,date from apply where bin_to_uuid(aid)=%s',[uid])
        cursor.close()
        uid,name,fname,religion,nationality,caste,handicaped,address,email,tmarks,imarks,date=cursor.fetchone()
        return render_template('viewapplication.html',name=name,fname=fname,religion=religion,nationality=nationality,caste=caste,handicaped=handicaped,address=address,email=email,tmarks=tmarks,imarks=imarks,date=date)
    else:
        return redirect(url_for('login'))
@app.route('/afid/<uid>')
def afid(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select extension,filedata from apply where bin_to_uuid(aid)=%s',[uid])
        ext,bin_data=cursor.fetchone()
        bytes_data=BytesIO(bin_data)
        filename=f'attachement.{ext}'
        return send_file(bytes_data,download_name=filename,as_attachment=False)
    else:   
        return redirect(url_for('login'))
@app.route('/adelete/<uid>')
def adelete(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('delete from apply where bin_to_uuid(aid)=%s',[uid])
        mydb.commit()
        cursor.close()
        flash('Application deleted successfully')
        return redirect(url_for('viewapplication'))
    else:
        return redirect(url_for('login'))
@app.route('/update/<uid>',methods=['GET','POST'])
def update(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(aid),name,fname,religion,nationality,caste,handicaped,address,email,tmarks,imarks,extension,filedata from apply where bin_to_uuid(aid)=%s',[uid])
        uid,name,fname,religion,nationality,caste,handicaped,address,email,tmarks,imarks,extension,filedata=cursor.fetchone()
        cursor.close()
        if request.method=='POST':
            name=request.form['name']
            fname=request.form['fname']
            religion=request.form['religion']
            nationality=request.form['nationality']
            caste=request.form['caste']
            handicaped=request.form['handicaped']
            address=request.form['address']
            email=request.form['email']
            tmarks=request.form['tmarks']
            imarks=request.form['imarks']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('update apply set name=%s,fname=%s,religion=%s,nationality=%s,caste=%s,handicaped=%s,address=%s,email=%s,tmarks=%s,imarks=%s where bin_to_uuid(aid)=%s',[name,fname,religion,nationality,caste,handicaped,address,email,tmarks,imarks,uid])
            mydb.commit()
            cursor.close()
            flash('Application upated successfully')
            return redirect(url_for('viewapplication'))
        return render_template('update.html',name=name,fname=fname,religion=religion,nationality=nationality,caste=caste,handicaped=handicaped,address=address,email=email,tmarks=tmarks,imarks=imarks)
    else:
        return redirect(url_for('login'))
@app.route('/astatus/<uid>')
def astatus(uid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select status from apply where bin_to_uuid(aid)=%s',[uid])
        status=cursor.fetchone()[0]
        cursor.close()
        return render_template('astatus.html',status=status)
    else:
        return redirect(url_for('login'))
app.run(debug=True,use_reloader=True)