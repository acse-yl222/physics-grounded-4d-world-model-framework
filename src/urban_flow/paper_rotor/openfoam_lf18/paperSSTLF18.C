// SPDX-License-Identifier: GPL-3.0-or-later
// Constant-density LF18 extension for OpenFOAM 2312.
// Equations: Larsen & Fuhrman (2018), authors' stabRAS_v1712 commit
// 46be844dcd54524c75a3ecdda381c66e1e6a0279. Not an author-supplied rotor solver.
#include "turbulentTransportModels.H"
#include "kOmegaSST.H"
#include "fvOptions.H"

namespace Foam { namespace RASModels {
template<class BasicTurbulenceModel>
class paperSSTLF18 : public kOmegaSST<BasicTurbulenceModel>
{
    using Base = kOmegaSST<BasicTurbulenceModel>;
    dimensionedScalar lambda2_;
protected:
    void correctNut(const volScalarField& S2) override
    {
        const volScalarField rotation2(2*magSqr(skew(fvc::grad(this->U_))));
        const dimensionedScalar smallRotation("smallRotation",dimless/sqr(dimTime),SMALL);
        this->nut_ = this->a1_*this->k_/max
        (
            this->a1_*lambda2_*this->beta1_/(this->betaStar_*this->gamma1_)
                *S2/(rotation2+smallRotation)*this->omega_,
            max(this->a1_*this->omega_,this->b1_*this->F2()*sqrt(S2))
        );
        this->nut_.correctBoundaryConditions();
        fv::options::New(this->mesh_).correct(this->nut_);
        BasicTurbulenceModel::correctNut();
    }
    void correctNut() override
    {
        correctNut(2*magSqr(symm(fvc::grad(this->U_))));
    }
    tmp<volScalarField::Internal> GbyNu
    (
        const volScalarField::Internal&,
        const volScalarField::Internal&,
        const volScalarField::Internal& S2
    ) const override
    {
        // The authors' stabilized implementation uses unbounded gamma*S2.
        return tmp<volScalarField::Internal>(new volScalarField::Internal(S2));
    }
public:
    using alphaField = typename BasicTurbulenceModel::alphaField;
    using rhoField = typename BasicTurbulenceModel::rhoField;
    using transportModel = typename BasicTurbulenceModel::transportModel;
    TypeName("paperSSTLF18");
    paperSSTLF18
    (
        const alphaField& alpha, const rhoField& rho, const volVectorField& U,
        const surfaceScalarField& alphaRhoPhi, const surfaceScalarField& phi,
        const transportModel& transport,
        const word& propertiesName=turbulenceModel::propertiesName,
        const word& type=typeName
    ) : Base(alpha,rho,U,alphaRhoPhi,phi,transport,propertiesName,type),
        lambda2_("lambda2",dimless,0.05)
    {
        // Fixed coefficient intentionally matches the separate PyTorch variant.
        correctNut();
    }
};
}}
makeRASModel(paperSSTLF18);
