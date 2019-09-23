import numpy as np
from numpy.linalg import norm 
from liegroups.numpy import SO3
import matplotlib.pylab as plt
import cvxpy as cp

#Helpers
##########
def Omega_1(q):
    Om = np.zeros((4,4)) * np.nan
    np.fill_diagonal(Om, q[3]) 
    
    Om[0,1] = -q[2]
    Om[0,2] = q[1]
    Om[0,3] = q[0]

    Om[1,0] = q[2]
    Om[1,2] = -q[0]
    Om[1,3] = q[1]

    Om[2,0] = -q[1]
    Om[2,1] = q[0]
    Om[2,3] = q[2]
    
    Om[3,0] = -q[0]
    Om[3,1] = -q[1]
    Om[3,2] = -q[2]

    return Om

def Omega_2(q):
    Om = np.zeros((4,4)) * np.nan
    np.fill_diagonal(Om, q[3]) 
    
    Om[0,1] = q[2]
    Om[0,2] = -q[1]
    Om[0,3] = q[0]

    Om[1,0] = -q[2]
    Om[1,2] = q[0]
    Om[1,3] = q[1]

    Om[2,0] = q[1]
    Om[2,1] = -q[0]
    Om[2,3] = q[2]
    
    Om[3,0] = -q[0]
    Om[3,1] = -q[1]
    Om[3,2] = -q[2]

    return Om

def pure_quat(v):
    q = np.zeros(4)
    q[:3] = v
    return q

def Q_ii(a_i, b_i, c_bar_2, sigma_2_i):
    I = np.eye(4)
    t1 = (b_i.dot(b_i) + a_i.dot(a_i))*I
    t2 = 2*Omega_1(pure_quat(b_i)).dot(
        Omega_2(pure_quat(a_i))
        )
    Q = (t1 + t2)/(2*sigma_2_i) + 0.5*c_bar_2*I
    return Q

def Q_0i(a_i, b_i, c_bar_2, sigma_2_i):
    I = np.eye(4)
    t1 = (b_i.dot(b_i) + a_i.dot(a_i))*I
    t2 = 2*Omega_1(pure_quat(b_i)).dot(
        Omega_2(pure_quat(a_i))
        )
    Q = (t1 + t2)/(4*sigma_2_i) - 0.25*c_bar_2*I
    return Q

def q_from_qqT(qqT):
    #Returns unit quaternion q from q * q^T 4x4 matrix
    #Assumes scalar is the last value and it is positive (can make this choice since q = -q)

    q = np.sqrt(np.diag(qqT))
    if qqT[0,3] < 0.:
        q[0] *=  -1.
    if qqT[1,3] < 0.:
        q[1] *=  -1.
    if qqT[2,3] < 0.:
        q[2] *=  -1.

    return q
######

##Parameters

#Sim
N = 10
sigma = 0.01

#Solver
sigma_2_i = 0.5**2
c_bar_2 = 10**2


##Simulation
#Create a random rotation
C = SO3.exp(np.random.randn(3)).as_matrix()

#Create two sets of vectors 
x_1= np.random.rand(N, 3) 

#Rotate and add noise
x_2 = C.dot(x_1.T).T + sigma*np.random.randn(N,3)

## Solver
#Build Q matrix
#No sparsity for now
Q = np.zeros((4*(N+1), 4*(N+1)))

for i in range(N): 
    Q_i = np.zeros((4*(N+1), 4*(N+1)))
    for ii in range(N):
        #Block diagonal indices
        idx_range = slice( (ii+1)*4 , (ii+2)*4 )
        
        Q_i[idx_range, idx_range] = Q_ii(x_1[ii], x_2[ii], c_bar_2, sigma_2_i)
        Q_0ii =  Q_0i(x_1[ii], x_2[ii], c_bar_2, sigma_2_i)
        Q_i[:4, idx_range] = Q_0ii
        Q_i[idx_range, :4] = Q_0ii

    Q += Q_i

#Optional: visualize matrix
# plt.spy(Q)
# plt.show()

#Build Z variable with constraints
Z = cp.Variable((4*(N+1),4*(N+1)), symmetric=True)
constraints = [Z >> 0]
constraints += [
    cp.trace(Z[:4,:4]) == 1
]
constraints += [
    Z[(i)*4:(i+1)*4, (i)*4:(i+1)*4] == Z[:4,:4] for i in range(1, N)
]

#Solve SDP
prob = cp.Problem(cp.Minimize(cp.trace(Q@Z)),
                  constraints)
prob.solve()
print("status:", prob.status)
#print(Z.value)
q_est = q_from_qqT(Z.value[:4,:4])
print(q_est)

C_est = SO3.from_quaternion(q_est, ordering='xyzw').as_matrix()

#Compare to known rotation
# C_est = C
print('Frob norm error:')
print(np.linalg.norm(C-C_est))