import turtle as t

#=============hength of the block==============
a=50

#=============define fast entrances=======================
def up():
    t.up()

def down():
    t.pendown()

def goto(x,y):
    t.goto(x*a,y*a)  
    
def c(r,angle):
    t.circle(r*a,angle)
    
def l():
    t.left()
    
def r():
    t.right()    
    
def face(angle):				
    t.setheading(angle) 

def fillcolor(color):
    t.fillcolor(color)
def beginfill():
    t.begin_fill()
    
def endfill():
    t.end_fill()
    
    
    
    
#==========init============================================
t.pensize(15)
t.speed(0)
t.pencolor('black')
t.shape('arrow')
t.setheading(0)



#==========main programme==================================


#Draw the 'm' part 
up()
goto(0,0)
goto(0.5,0)
down()
fillcolor('cornflowerblue')
beginfill()
goto(3.5,0)
c(-1,90)
goto(4.5,-4)
goto(3.5,-4)
goto(3.5,-1)
goto(2.5,-1)
goto(2.5,-4)
goto(1.5,-4)
goto(1.5,-1)
goto(0.5,-1)
goto(0.5,-4)
goto(-0.5,-4)
goto(-0.5,-1)
face(-90)
c(1,-90)
endfill()
up()


#Draw the 'i' part 

face(0)
goto(-1.5,-0.5)
fillcolor('red')
beginfill()
down()
goto(-1.5,-1.5)
goto(-2.5,-1.5)
goto(-2.5,-0.5)
goto(-1.5,-0.5)
endfill()
up()

goto(-1.5,-2)
down()
fillcolor('yellow')
beginfill()
goto(-1.5,-4)
goto(-2.5,-4)
goto(-2.5,-2)
goto(-1.5,-2)
up()
endfill()
t.done()








